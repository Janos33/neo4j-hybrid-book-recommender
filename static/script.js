const AGE_OPTIONS = [
    { id: "0-12", label: "0 - 12 év (Gyermekek)" },
    { id: "13-17", label: "13 - 17 év (Tinédzserek)" },
    { id: "18-25", label: "18 - 25 év (Fiatal felnőttek)" },
    { id: "26-40", label: "26 - 40 év (Felnőttek)" },
    { id: "41-60", label: "41 - 60 év (Középkorúak)" },
    { id: "60+",    label: "60+ év (Idősebb korosztály)" }
];

function updateInputsVisibility() {
    const contentWeight = parseInt(document.getElementById("contentWeight").value);
    const collabWeight = parseInt(document.getElementById("collabWeight").value);

    
    document.getElementById("contentVal").innerText = `Súly: ${contentWeight}%`;
    document.getElementById("collabVal").innerText = `Súly: ${collabWeight}%`;

    
    const contentDependentIds = ["genreContent", "prefAuthorContent"];
    
    contentDependentIds.forEach(id => {
        const el = document.getElementById(id);
        if (contentWeight > 0) {
            el.classList.remove("disabled-input");
        } else {
            el.classList.add("disabled-input");
        }
    });

    
    const bookContent = document.getElementById("bookContent");
    if (contentWeight > 0 || collabWeight > 0) {
        bookContent.classList.remove("disabled-input");
    } else {
        bookContent.classList.add("disabled-input");
    }
}

function updateToggle(toggle, content, label) {
    if(toggle.checked) {
        content.classList.remove("disabled-input");
        label.innerText = "Bekapcsolva";
        label.style.color = "var(--primary-brown)";
    } else {
        content.classList.add("disabled-input");
        label.innerText = "Kikapcsolva";
        label.style.color = "var(--text-muted)";
    }
}


function setupTagInput(inputId, listId, containerId, mode, dataSource) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    const container = document.getElementById(containerId);
    let selectedItems = [];

    function renderTags() {
        const inputEl = container.querySelector('input');
        container.innerHTML = "";
        selectedItems.forEach(item => {
            const tag = document.createElement("div");
            tag.classList.add("tag");
            const labelText = item.extra ? `${item.label} <small>(${item.extra})</small>` : item.label;
            tag.innerHTML = `${labelText} <span>&times;</span>`;
            tag.querySelector("span").addEventListener("click", () => {
                selectedItems = selectedItems.filter(i => i.id !== item.id);
                renderTags();
            });
            container.appendChild(tag);
        });
        container.appendChild(inputEl);
        inputEl.focus();
    }

    async function showSuggestions(query) {
        list.innerHTML = "";
        let results = [];
        if (mode === 'static') {
            results = dataSource.filter(opt => opt.label.toLowerCase().includes(query.toLowerCase()));
        } else {
            if (query.length < 2) return;
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${dataSource}`);
                results = await res.json();
            } catch(e) { console.error(e); }
        }
        if (results.length === 0) return;
        results.forEach(item => {
            if (selectedItems.some(s => s.id === item.id)) return;
            const div = document.createElement("div");
            div.classList.add("autocomplete-item");
            if(mode === 'static') div.classList.add("static-option");
            div.innerHTML = item.extra ? `<strong>${item.label}</strong> <small>(${item.extra})</small>` : `<strong>${item.label}</strong>`;
            div.addEventListener("click", () => {
                selectedItems.push(item);
                renderTags();
                input.value = "";
                list.innerHTML = "";
                const parentSection = container.closest('.form-section');
                if (parentSection) {
                    const toggle = parentSection.querySelector('input[type="checkbox"]');
                    if(toggle && !toggle.checked) {
                        toggle.checked = true;
                        
                        toggle.dispatchEvent(new Event('change'));
                    }
                }
            });
            list.appendChild(div);
        });
    }

    input.addEventListener("input", (e) => showSuggestions(e.target.value.trim()));
    if(mode === 'static') input.addEventListener("click", () => showSuggestions(""));
    document.addEventListener("click", e => {
        if (!e.target.closest(`#${containerId}`) && !e.target.closest(`#${listId}`)) list.innerHTML = "";
    });

    return { 
        getSelected: () => selectedItems,
        addTag: (item) => {
            if (!selectedItems.some(s => s.id === item.id)) {
                selectedItems.push(item);
                renderTags();
            }
        },
        clear: () => {
            selectedItems = [];
            renderTags();
        }
    };
}

document.addEventListener("DOMContentLoaded", () => {
    
    
    document.getElementById("recommendForm").reset();

    
    const ageManager = setupTagInput("ageSearch", "listAge", "selectedAgeContainer", "static", AGE_OPTIONS);
    const constAuthorManager = setupTagInput("constAuthorSearch", "autocompleteListConstAuthors", "selectedConstAuthorsContainer", "async", "author");
    const constGenreManager = setupTagInput("constGenreSearch", "autocompleteListConstGenres", "selectedConstGenresContainer", "async", "genre");

    const exclAuthorManager = setupTagInput("exclAuthorSearch", "autocompleteListExclAuthors", "selectedExclAuthorsContainer", "async", "author");
    const exclGenreManager = setupTagInput("exclGenreSearch", "autocompleteListExclGenres", "selectedExclGenresContainer", "async", "genre");

    const genreManager = setupTagInput("genreSearch", "autocompleteListGenres", "selectedGenresContainer", "async", "genre");
    const prefAuthorManager = setupTagInput("prefAuthorSearch", "autocompleteListPrefAuthors", "selectedPrefAuthorsContainer", "async", "author");
    const bookManager = setupTagInput("bookSearch", "autocompleteListBooks", "selectedBooksContainer", "async", "book");

    const managers = {
        ageManager, constAuthorManager, constGenreManager,
        exclAuthorManager, exclGenreManager,
        genreManager, prefAuthorManager, bookManager
    };

    
    const toggles = [
        { id: "ageToggle", content: "ageContent", label: "ageToggleLabel" },
        { id: "pubToggle", content: "pubContent", label: "pubToggleLabel" },
        { id: "constAuthorToggle", content: "constAuthorContent", label: "constAuthorToggleLabel" },
        { id: "constGenreToggle", content: "constGenreContent", label: "constGenreToggleLabel" },
        { id: "exclAuthorToggle", content: "exclAuthorContent", label: "exclAuthorToggleLabel" },
        { id: "exclGenreToggle", content: "exclGenreContent", label: "exclGenreToggleLabel" }
    ];

    
    toggles.forEach(t => {
        const el = document.getElementById(t.id);
        el.addEventListener("change", () => updateToggle(el, document.getElementById(t.content), document.getElementById(t.label)));
        
        updateToggle(el, document.getElementById(t.content), document.getElementById(t.label));
    });

    
    document.getElementById("contentWeight").addEventListener("input", updateInputsVisibility);
    document.getElementById("collabWeight").addEventListener("input", updateInputsVisibility);
    
    
    updateInputsVisibility();

    document.getElementById("minRating").addEventListener("input", (e) => {
        const val = parseInt(e.target.value) / 10;
        const label = document.getElementById("minRatingVal");
        if(val === 0) label.innerText = "Bármi";
        else if(val === 5) label.innerText = "5.0 Csillag";
        else label.innerText = `${val}+ Csillag`;
    });
    
    document.getElementById("randomness").addEventListener("input", (e) => {
        document.getElementById("randomnessVal").innerText = `${e.target.value}%`;
    });

    const autoEnablePeriod = () => {
        const toggle = document.getElementById("pubToggle");
        if (!toggle.checked) {
            toggle.checked = true;
            toggle.dispatchEvent(new Event('change')); 
        }
    };
    document.getElementById("yearStart").addEventListener("input", autoEnablePeriod);
    document.getElementById("yearEnd").addEventListener("input", autoEnablePeriod);


    
    function saveState() {
        const state = {
            toggles: {},
            inputs: {},
            tags: {}
        };
        
        toggles.forEach(t => state.toggles[t.id] = document.getElementById(t.id).checked);
        
        
        const inputIds = ["contentWeight", "collabWeight", "minRating", "randomness", "limitInput", "yearStart", "yearEnd"];
        inputIds.forEach(id => state.inputs[id] = document.getElementById(id).value);

        
        for (const [key, mgr] of Object.entries(managers)) {
            state.tags[key] = mgr.getSelected();
        }
        sessionStorage.setItem("bookRecommenderState", JSON.stringify(state));
    }

    function restoreState() {
        const raw = sessionStorage.getItem("bookRecommenderState");
        if (!raw) return;

        try {
            const state = JSON.parse(raw);
            
            
            for (const [id, val] of Object.entries(state.inputs)) {
                const el = document.getElementById(id);
                if(el) { 
                    el.value = val; 
                    
                    el.dispatchEvent(new Event('input')); 
                }
            }

            
            if (state.toggles) {
                toggles.forEach(t => {
                    const el = document.getElementById(t.id);
                    const savedState = state.toggles[t.id];
                    if (el && savedState !== undefined) {
                        el.checked = savedState;
                        
                        updateToggle(el, document.getElementById(t.content), document.getElementById(t.label));
                    }
                });
            }

            
            for (const [key, items] of Object.entries(state.tags)) {
                if(managers[key]) {
                    managers[key].clear();
                    items.forEach(item => managers[key].addTag(item));
                }
            }

            
            updateInputsVisibility();

        } catch(e) {
            console.error("State restore failed", e);
            sessionStorage.removeItem("bookRecommenderState");
        }
    }

    function clearState() {
        sessionStorage.removeItem("bookRecommenderState");
        window.location.reload();
    }

    document.getElementById("clearFormBtn").addEventListener("click", clearState);

    
    restoreState();


    document.getElementById("recommendForm").addEventListener("submit", async function (e) {
        e.preventDefault();
        saveState(); 

        const btn = this.querySelector("button[type='submit']");
        const originalText = btn.innerText;
        btn.innerText = "Feldolgozás...";
        btn.disabled = true;
        
        const getVal = (mgr) => mgr.getSelected().map(x => x.id);
        const contentW = parseInt(document.getElementById("contentWeight").value);
        const collabW = parseInt(document.getElementById("collabWeight").value);

        const payload = {
            constraints: {
                age: { active: document.getElementById("ageToggle").checked, values: getVal(ageManager) },
                period: { 
                    active: document.getElementById("pubToggle").checked, 
                    custom_min: document.getElementById("yearStart").value,
                    custom_max: document.getElementById("yearEnd").value
                },
                authors: { active: document.getElementById("constAuthorToggle").checked, values: getVal(constAuthorManager) },
                genres: { active: document.getElementById("constGenreToggle").checked, values: getVal(constGenreManager) },
                excluded_authors: { active: document.getElementById("exclAuthorToggle").checked, values: getVal(exclAuthorManager) },
                excluded_genres: { active: document.getElementById("exclGenreToggle").checked, values: getVal(exclGenreManager) }
            },
            preferences: {
                genres: { weight: contentW, values: getVal(genreManager) },
                authors: { weight: contentW, values: getVal(prefAuthorManager) },
                books: { values: getVal(bookManager), weight_content: contentW, weight_collab: collabW }
            },
            settings: {
                min_rating: parseInt(document.getElementById("minRating").value) / 10,
                randomness: parseInt(document.getElementById("randomness").value) / 100,
                limit: parseInt(document.getElementById("limitInput").value)
            }
        };

        try {
            const response = await fetch('/recommend', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if(response.ok) {
                document.open();
                document.write(await response.text());
                document.close();
            } else { throw new Error("Server Error"); }
        } catch (err) { 
            console.error(err);
            alert("Hiba történt a kommunikációban."); 
            btn.innerText = originalText;
            btn.disabled = false;
        }
    });
});