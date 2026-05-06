// Alpine factory for the settings page. Initial state (current config + which
// keys are overridden) is rendered server-side into data-* attributes on a
// hidden #settings-init-data element so this script can stay CSP-clean —
// no inline JSON, no inline scripts, no eval beyond Alpine's own expression
// evaluator.
function settingsPage() {
    const dataEl = document.getElementById('settings-init-data');
    return {
        config: JSON.parse(dataEl.dataset.config),
        overrides: JSON.parse(dataEl.dataset.overrides),
        message: '',
        messageError: false,
        init() {},
        isOverridden(key) {
            return key in this.overrides;
        },
        async saveGeneral(attr, value, event) {
            await this.saveOverride(`general.${attr}`, value, event);
        },
        async saveJob(jobName, attr, value, event) {
            await this.saveOverride(`jobs.${jobName}.${attr}`, value, event);
        },
        flashEl(event, cls) {
            if (!event) return;
            const el = event.target.closest('label') || event.target;
            el.classList.remove('flash-save', 'flash-error');
            void el.offsetWidth;
            el.classList.add(cls);
            el.addEventListener('animationend', () => el.classList.remove(cls), { once: true });
        },
        async saveOverride(key, value, event) {
            try {
                const res = await fetch(rootPath + '/api/config', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates: { [key]: value } }),
                });
                if (res.ok) {
                    this.overrides[key] = value;
                    this.flashEl(event, 'flash-save');
                } else {
                    this.flashEl(event, 'flash-error');
                }
            } catch {
                this.flashEl(event, 'flash-error');
            }
        },
        async resetOverrides() {
            if (!confirm('Reset all runtime overrides to YAML defaults? This will reload settings from config file.')) return;
            try {
                const res = await fetch(rootPath + '/api/config/reload', { method: 'POST' });
                if (res.ok) {
                    this.overrides = {};
                    this.showMessage('Reset to defaults');
                    setTimeout(() => location.reload(), 500);
                }
            } catch {
                this.showMessage('Error resetting', true);
            }
        },
        showMessage(msg, error = false) {
            this.message = msg;
            this.messageError = error;
            setTimeout(() => this.message = '', 3000);
        },
    };
}
