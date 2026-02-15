function app() {
  return {
    // State
    groups: [],
    selectedGroupId: null,
    selectedGroupDetail: null,
    selectedSessionId: null,
    selectedSession: null,
    messages: [],
    messagesLoading: false,
    searchOpen: false,
    searchQuery: '',
    searchResults: [],
    sidebarFilter: '',
    cloneExpanded: {},
    copyFeedback: false,
    contextSession: null,

    // Computed
    get selectedGroup() {
      return this.groups.find(g => g.group_id === this.selectedGroupId) || null;
    },

    get pinnedSessions() {
      if (!this.selectedGroupDetail) return [];
      const pinned = [];
      for (const clone of this.selectedGroupDetail.clones || []) {
        for (const s of clone.sessions || []) {
          if (s.is_pinned) pinned.push(s);
        }
      }
      return pinned;
    },

    get filteredClones() {
      if (!this.selectedGroupDetail) return [];
      return this.selectedGroupDetail.clones || [];
    },

    get recentSessions() {
      if (!this.selectedGroupDetail) return [];
      const all = [];
      for (const clone of this.selectedGroupDetail.clones || []) {
        for (const s of clone.sessions || []) {
          all.push({ ...s, clone_name: clone.clone_name });
        }
      }
      all.sort((a, b) => new Date(b.modified) - new Date(a.modified));
      return all.slice(0, 10);
    },

    // Methods
    async init() {
      await this.loadGroups();
      this.connectSSE();

      // Request notification permission
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    },

    async loadGroups() {
      try {
        const res = await fetch('/api/groups');
        const data = await res.json();
        this.groups = data.groups || [];

        // Auto-select first group if none selected
        if (!this.selectedGroupId && this.groups.length > 0) {
          this.selectGroup(this.groups[0].group_id);
        }
      } catch (e) {
        console.error('Failed to load groups:', e);
      }
    },

    async selectGroup(groupId) {
      this.selectedGroupId = groupId;
      this.selectedSessionId = null;
      this.selectedSession = null;
      this.messages = [];

      try {
        const res = await fetch(`/api/groups/${encodeURIComponent(groupId)}`);
        this.selectedGroupDetail = await res.json();

        // Expand all clones by default
        for (const clone of this.selectedGroupDetail.clones || []) {
          if (!(clone.clone_id in this.cloneExpanded)) {
            this.cloneExpanded[clone.clone_id] = true;
          }
        }
      } catch (e) {
        console.error('Failed to load group:', e);
      }
    },

    async openSession(sessionId) {
      this.selectedSessionId = sessionId;
      this.messagesLoading = true;

      try {
        // Load session detail
        const res = await fetch(`/api/sessions/${sessionId}`);
        this.selectedSession = await res.json();

        // Load messages
        const msgRes = await fetch(`/api/sessions/${sessionId}/messages?limit=100`);
        const msgData = await msgRes.json();
        this.messages = msgData.messages || [];

        // Scroll to bottom
        this.$nextTick(() => {
          const area = this.$refs.messageArea;
          if (area) area.scrollTop = area.scrollHeight;
        });
      } catch (e) {
        console.error('Failed to load session:', e);
      } finally {
        this.messagesLoading = false;
      }
    },

    async selectSession(groupId, sessionId) {
      if (this.selectedGroupId !== groupId) {
        await this.selectGroup(groupId);
      }
      await this.openSession(sessionId);
    },

    toggleClone(cloneId) {
      this.cloneExpanded[cloneId] = !this.cloneExpanded[cloneId];
    },

    matchesFilter(session) {
      if (!this.sidebarFilter) return true;
      const q = this.sidebarFilter.toLowerCase();
      const name = (session.display_name || '').toLowerCase();
      const prompt = (session.first_prompt || '').toLowerCase();
      const branch = (session.git_branch || '').toLowerCase();
      return name.includes(q) || prompt.includes(q) || branch.includes(q);
    },

    async doSearch() {
      if (!this.searchQuery.trim()) {
        this.searchResults = [];
        return;
      }
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(this.searchQuery)}`);
        const data = await res.json();
        this.searchResults = data.results || [];
      } catch (e) {
        console.error('Search failed:', e);
      }
    },

    async resumeSession(sessionId) {
      try {
        const res = await fetch(`/api/sessions/${sessionId}/resume`, { method: 'POST' });
        const data = await res.json();
        if (!data.success && data.command) {
          // Fallback: copy command
          await navigator.clipboard.writeText(data.command);
          this.showCopyFeedback();
        }
      } catch (e) {
        console.error('Resume failed:', e);
      }
    },

    async copyResumeCommand(sessionId) {
      if (!this.selectedSession) return;
      const cmd = `cd ${this.selectedSession.project_path} && claude --resume ${sessionId}`;
      try {
        await navigator.clipboard.writeText(cmd);
        this.showCopyFeedback();
      } catch (e) {
        console.error('Copy failed:', e);
      }
    },

    showCopyFeedback() {
      this.copyFeedback = true;
      setTimeout(() => { this.copyFeedback = false; }, 2000);
    },

    async toggleSessionPin(sessionId) {
      try {
        const res = await fetch(`/api/sessions/${sessionId}/pin`, { method: 'PUT' });
        const data = await res.json();
        if (this.selectedSession && this.selectedSession.session_id === sessionId) {
          this.selectedSession.is_pinned = data.is_pinned;
        }
        // Refresh group detail
        await this.selectGroup(this.selectedGroupId);
        // Re-open session to keep it selected
        if (this.selectedSessionId) {
          this.selectedSessionId = sessionId;
        }
      } catch (e) {
        console.error('Pin toggle failed:', e);
      }
    },

    connectSSE() {
      const evtSource = new EventSource('/api/events');
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'index_refreshed') {
            this.loadGroups();
            if (this.selectedGroupId) {
              this.selectGroup(this.selectedGroupId);
            }
          }
        } catch (e) {
          // ignore parse errors
        }
      };
      evtSource.onerror = () => {
        // Reconnect after 5 seconds
        setTimeout(() => this.connectSSE(), 5000);
      };
    },

    // --- Display helpers ---

    statusColor(status) {
      const map = {
        active: 'bg-green-500',
        recent: 'bg-yellow-500',
        idle: 'bg-gray-500',
        archived: 'bg-gray-700',
      };
      return map[status] || 'bg-gray-600';
    },

    timeAgo(isoStr) {
      if (!isoStr) return '';
      const diff = Date.now() - new Date(isoStr).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return 'たった今';
      if (mins < 60) return `${mins}分前`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `${hours}時間前`;
      const days = Math.floor(hours / 24);
      if (days < 30) return `${days}日前`;
      const months = Math.floor(days / 30);
      return `${months}ヶ月前`;
    },

    formatDate(isoStr) {
      if (!isoStr) return '';
      const d = new Date(isoStr);
      return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
    },

    formatDateFull(isoStr) {
      if (!isoStr) return '';
      const d = new Date(isoStr);
      const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
      return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日（${weekdays[d.getDay()]}）`;
    },

    formatTime(isoStr) {
      if (!isoStr) return '';
      const d = new Date(isoStr);
      return `${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
    },

    dateDiffersFrom(msg, prevMsg) {
      if (!prevMsg || !msg.timestamp || !prevMsg.timestamp) return false;
      const d1 = new Date(msg.timestamp);
      const d2 = new Date(prevMsg.timestamp);
      return d1.toDateString() !== d2.toDateString();
    },

    renderContent(text) {
      if (!text) return '';
      // Simple markdown-like rendering
      let html = this.escapeHtml(text);
      // Code blocks
      html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
        '<pre class="bg-[#16181c] rounded-md p-3 my-2 text-sm overflow-x-auto border border-slack-border/30"><code>$2</code></pre>');
      // Inline code
      html = html.replace(/`([^`]+)`/g,
        '<code class="bg-[#35373b] px-1.5 py-0.5 rounded text-sm text-pink-300">$1</code>');
      // Bold
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-bold">$1</strong>');
      // Newlines
      html = html.replace(/\n/g, '<br>');
      return html;
    },

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    showContextMenu(event) {
      // Simple context menu - for now just a placeholder
      // Can be extended later
    },
  };
}
