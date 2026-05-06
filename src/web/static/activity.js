// Alpine factory for the activity log page. Owns the filter state, paginated
// fetch against /api/activity, and timestamp formatting.
function activityLog() {
    return {
        items: [],
        loading: true,
        page: 1,
        totalPages: 1,
        total: 0,
        filters: {
            search: '',
            action: '',
            arr: '',
            date_from: '',
            date_to: '',
        },
        async loadActivity() {
            this.loading = true;
            const params = new URLSearchParams({ page: this.page, per_page: 50 });
            if (this.filters.search) params.set('search', this.filters.search);
            if (this.filters.action) params.set('action', this.filters.action);
            if (this.filters.arr) params.set('arr', this.filters.arr);
            if (this.filters.date_from) params.set('date_from', this.filters.date_from);
            if (this.filters.date_to) params.set('date_to', this.filters.date_to);

            try {
                const res = await fetch(`${rootPath}/api/activity?${params}`);
                const data = await res.json();
                this.items = data.items;
                this.total = data.total;
                this.totalPages = data.total_pages;
            } catch {
                this.items = [];
            }
            this.loading = false;
        },
        formatTime(ts) {
            if (!ts) return '';
            const d = new Date(ts + 'Z');
            return d.toLocaleString();
        },
        prevPage() {
            if (this.page > 1) { this.page--; this.loadActivity(); }
        },
        nextPage() {
            if (this.page < this.totalPages) { this.page++; this.loadActivity(); }
        },
    };
}
