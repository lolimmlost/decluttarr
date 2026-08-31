// Settings page component. Registered via Alpine.data() for the CSP build of
// Alpine (no eval evaluator). Initial state (current config + which keys are
// overridden) is rendered server-side into data-* attributes on a hidden
// #settings-init-data element, so there is no inline JSON or inline script.
//
// The CSP evaluator only resolves bare property/method paths — no operators,
// object literals, `in`, or calls with arguments. So instead of inline
// expressions like @change="saveGeneral('timer', config.general.timer, $event)"
// the template tags each control with data-key / data-job / data-attr, and the
// generic saveField / saveJobField handlers read that context off the element.
document.addEventListener('alpine:init', () => {
    Alpine.data('settingsPage', () => {
        const dataEl = document.getElementById('settings-init-data');
        return {
            config: JSON.parse(dataEl.dataset.config),
            overrides: JSON.parse(dataEl.dataset.overrides),
            ov: { general: {} },
            message: '',
            messageError: false,
            init() {
                // Flag optional fields + derive the enabled label per job, since
                // the template cannot compute `'x' in jobConfig` or `!enabled`.
                for (const name in this.config.jobs) {
                    const j = this.config.jobs[name];
                    j.hasMaxStrikes = 'max_strikes' in j;
                    j.hasMinSpeed = 'min_speed' in j;
                    this.applyEnabledLabel(j);
                }
                this.rebuildOv();
            },
            get messageStyle() {
                return this.messageError
                    ? 'color: var(--pico-del-color)'
                    : 'color: var(--pico-ins-color)';
            },
            applyEnabledLabel(job) {
                job.enabledLabel = job.enabled ? 'enabled' : 'disabled';
                job.enabledClass = job.enabled ? 'status-enabled' : 'status-disabled';
            },
            // Build a nested mirror of the flat dotted override keys so the
            // template can test x-show="ov.general.timer" (a plain dot path).
            rebuildOv() {
                const ov = { general: {} };
                for (const key in this.overrides) {
                    const parts = key.split('.');
                    let cur = ov;
                    for (let i = 0; i < parts.length - 1; i++) {
                        cur[parts[i]] = cur[parts[i]] || {};
                        cur = cur[parts[i]];
                    }
                    cur[parts[parts.length - 1]] = true;
                }
                this.ov = ov;
            },
            fieldValue(el) {
                if (el.type === 'checkbox') return el.checked;
                if (el.type === 'number') return el.value === '' ? null : Number(el.value);
                return el.value;
            },
            saveField(e) {
                this.saveOverride(e.target.dataset.key, this.fieldValue(e.target), e);
            },
            saveJobField(e) {
                const { job, attr } = e.target.dataset;
                const value = this.fieldValue(e.target);
                if (attr === 'enabled') {
                    this.config.jobs[job].enabled = value;
                    this.applyEnabledLabel(this.config.jobs[job]);
                }
                this.saveOverride(`jobs.${job}.${attr}`, value, e);
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
                        this.rebuildOv();
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
                        this.rebuildOv();
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
    });
});
