/* Reusable searchable tag picker.
 * Usage: var picker = initTagPicker(containerEl, {
 *          suggestions: [...], initial: [...], allowFree: true,
 *          placeholder: 'Type to search…', onChange: function(selectedArray){}
 *        });
 *        picker.get() -> array; picker.set([...]); picker.reset();
 */
(function () {
    function initTagPicker(container, opts) {
        opts = opts || {};
        var suggestions = opts.suggestions || [];
        var allowFree = opts.allowFree !== false;
        var onChange = opts.onChange || function () {};
        var selected = (opts.initial || []).slice();

        container.className = (container.className ? container.className + ' ' : '') + 'tag-picker';
        container.innerHTML = '';

        var chipWrap = document.createElement('div');
        chipWrap.className = 'tp-chips';
        var input = document.createElement('input');
        input.type = 'text';
        input.className = 'tp-input form-control';
        input.placeholder = opts.placeholder || 'Type to search/add…';
        input.autocomplete = 'off';
        var dropdown = document.createElement('div');
        dropdown.className = 'tp-dropdown';

        container.appendChild(chipWrap);
        container.appendChild(input);
        container.appendChild(dropdown);

        function emit() { onChange(selected.slice()); }

        function render() {
            chipWrap.innerHTML = '';
            selected.forEach(function (tag, idx) {
                var chip = document.createElement('span');
                chip.className = 'tp-chip';
                var txt = document.createElement('span'); txt.className = 'tp-chip-text'; txt.textContent = tag;
                var x = document.createElement('span'); x.className = 'tp-chip-x'; x.innerHTML = '&times;'; x.title = 'remove';
                x.addEventListener('click', function () { selected.splice(idx, 1); render(); emit(); });
                chip.appendChild(txt); chip.appendChild(x);
                chipWrap.appendChild(chip);
            });
        }

        function addTag(tag) {
            tag = (tag || '').trim();
            if (!tag) return;
            if (selected.map(function (s) { return s.toLowerCase(); }).indexOf(tag.toLowerCase()) !== -1) return;
            selected.push(tag); render(); emit();
        }

        function showDropdown() {
            var q = input.value.trim().toLowerCase();
            var matches = suggestions.filter(function (s) { return !q || s.toLowerCase().indexOf(q) !== -1; });
            var lowerSuggestions = suggestions.map(function (s) { return s.toLowerCase(); });
            var isNew = allowFree && input.value.trim() && lowerSuggestions.indexOf(input.value.trim().toLowerCase()) === -1;
            if (!matches.length && !isNew) { dropdown.innerHTML = '<div class="tp-empty">No matches</div>'; dropdown.style.display = 'block'; return; }
            dropdown.innerHTML = '';
            matches.slice(0, 12).forEach(function (s) {
                var item = document.createElement('div');
                item.className = 'tp-item'; item.textContent = s;
                item.addEventListener('mousedown', function (e) { e.preventDefault(); addTag(s); input.value = ''; hide(); });
                dropdown.appendChild(item);
            });
            if (isNew) {
                var item = document.createElement('div');
                item.className = 'tp-item tp-item-new';
                item.innerHTML = '+ Add new: <strong></strong>';
                item.querySelector('strong').textContent = input.value.trim();
                item.addEventListener('mousedown', function (e) { e.preventDefault(); addTag(input.value.trim()); input.value = ''; hide(); });
                dropdown.appendChild(item);
            }
            dropdown.style.display = 'block';
        }
        function hide() { dropdown.style.display = 'none'; }

        input.addEventListener('input', showDropdown);
        input.addEventListener('focus', showDropdown);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                var v = input.value.trim();
                if (v) { addTag(v); input.value = ''; hide(); }
            } else if (e.key === 'Backspace' && !input.value && selected.length) {
                selected.pop(); render(); emit();
            } else if (e.key === 'Escape') {
                hide();
            }
        });
        input.addEventListener('blur', function () { setTimeout(hide, 130); });

        render();
        return {
            get: function () { return selected.slice(); },
            set: function (arr) { selected = (arr || []).slice(); render(); emit(); },
            reset: function () { selected = []; render(); emit(); },
            setSuggestions: function (s) { suggestions = s || []; }
        };
    }

    window.initTagPicker = initTagPicker;
})();
