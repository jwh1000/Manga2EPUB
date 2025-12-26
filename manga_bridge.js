// ==UserScript==
// @name         Manga Bridge V9
// @namespace    http://tampermonkey.net/
// @version      9.0
// @description  Prioritizes data-src and retries corrupted images.
// @author       You
// @match        https://mangataro.org/read/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// ==/UserScript==

(function() {
    'use strict';

    const SERVER_URL = "http://127.0.0.1:5000";
    const SAVE_URL = "http://127.0.0.1:5000/save_page";
    const AUTO_START_KEY = 'manga_bridge_active';
    // Fast mode removed: always use smart/sync behavior
    const IMAGE_REGEX = /.*storage.*/;
    const MIN_HEIGHT = 300;

    // --- UI ---
    const container = document.createElement('div');
    container.style = `
        position: fixed; bottom: 20px; left: 20px; z-index: 9999;
        background: #2c3e50; padding: 10px; border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); color: white;
        font-family: sans-serif; display: flex; flex-direction: column; gap: 8px;
    `;
    document.body.appendChild(container);

    // Fast Mode toggle removed — the script will always perform smart syncing

    const btn = document.createElement('button');
    btn.innerHTML = '📡 Start Bridge';
    btn.style = "padding: 8px 12px; background: #3498db; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;";
    container.appendChild(btn);

    // --- LOGIC ---

    if (GM_getValue(AUTO_START_KEY, false)) {
        btn.innerHTML = '🛑 Stop Bridge';
        btn.style.background = '#c0392b';
        setTimeout(checkServerAndStart, 4000);
    }

    btn.onclick = function() {
        if (GM_getValue(AUTO_START_KEY, false)) {
            GM_setValue(AUTO_START_KEY, false);
            location.reload();
        } else {
            checkServerAndStart();
        }
    };

    function checkServerAndStart() {
        btn.innerHTML = "⏳ Connecting...";
        btn.style.background = "#f39c12";

        GM_xmlhttpRequest({
            method: "GET", url: SERVER_URL, timeout: 2000,
            onload: (r) => {
                if (r.status === 200) {
                    GM_setValue(AUTO_START_KEY, true);
                    btn.innerHTML = '🛑 Stop Bridge';
                    btn.style.background = '#c0392b';
                    startProcess();
                } else { serverFail(); }
            },
            onerror: serverFail, ontimeout: serverFail
        });
    }

    function serverFail() {
        alert("❌ Python Server Not Running!");
        btn.innerHTML = '📡 Start Bridge';
        btn.style.background = '#3498db';
        GM_setValue(AUTO_START_KEY, false);
    }

    async function startProcess() {
        // Always use Smart Syncing (slow/robust path)
        updateStatus("⬇️ Smart Syncing...");
        window.scrollTo(0,0);

        const images = Array.from(document.querySelectorAll('img')).filter(img =>
            (img.src && IMAGE_REGEX.test(img.src)) ||
            (img.getAttribute('data-src') && IMAGE_REGEX.test(img.getAttribute('data-src')))
        );

        const totalPagesEl = document.getElementById('totalPages');
        if (totalPagesEl) {
            const expected = parseInt(totalPagesEl.innerText.trim(), 10);
            if (!isNaN(expected) && images.length < expected) {
                await forceScroll();
                const retryImages = Array.from(document.querySelectorAll('img')).filter(img => IMAGE_REGEX.test(img.src || img.getAttribute('data-src')));
                if (retryImages.length < expected) {
                    GM_setValue(AUTO_START_KEY, false);
                    alert(`⚠️ Integrity Fail: Found ${retryImages.length}/${expected}. Stopping.`);
                    updateStatus("⚠️ Missing Pages");
                    return;
                }
            }
        }

        if (images.length === 0) {
            alert("No images found!");
            GM_setValue(AUTO_START_KEY, false);
            return;
        }

        const mangaTitle = getMangaTitle();
        const chapterTitle = getChapterTitle();

        // --- DOWNLOAD LOOP ---
        for (let i = 0; i < images.length; i++) {
            const img = images[i];

            const url = img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.src;
            const filename = `Page_${String(i).padStart(3, '0')}`;

            img.scrollIntoView({behavior: "auto", block: "center"});

            const ready = await waitForRealImage(img);
            if (!ready) console.warn(`Timeout waiting for image ${i}`);

            try {
                updateStatus(`📤 Sending ${i+1}/${images.length}...`);
                const base64Data = await fetchImageAsBase64(url);

                await sendToPython(mangaTitle, chapterTitle, filename, base64Data);

            } catch (e) {
                console.warn(`⚠️ Failed Page ${i}, Retrying in 3s...`);
                updateStatus(`⚠️ Retrying ${i+1}...`);

                await new Promise(r => setTimeout(r, 3000));

                const newUrl = img.src || img.getAttribute('data-src');
                try {
                     const newData = await fetchImageAsBase64(newUrl);
                     await sendToPython(mangaTitle, chapterTitle, filename, newData);
                     console.log(`✅ Retry success for Page ${i}`);
                } catch (retryErr) {
                     console.error(`❌ Retry failed for Page ${i}:`, retryErr);
                }
            }
        }

        updateStatus("➡️ Next Chapter...");
        setTimeout(goToNextChapter, 2000);
    }

    function waitForRealImage(img) {
        return new Promise((resolve) => {
            if (img.complete && img.naturalHeight > MIN_HEIGHT) return resolve(true);
            let retries = 0;
            const interval = setInterval(() => {
                if (img.complete && img.naturalHeight > MIN_HEIGHT) {
                    clearInterval(interval);
                    resolve(true);
                }
                retries++;
                if (retries > 60) { clearInterval(interval); resolve(false); }
            }, 100);
        });
    }

    // fastScroll removed — not used anymore

    async function forceScroll() {
        return new Promise(resolve => {
            let lastScroll = -1;
            const timer = setInterval(() => {
                window.scrollBy(0, 1000);
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 50) {
                    if (window.scrollY === lastScroll) { clearInterval(timer); resolve(); }
                }
                lastScroll = window.scrollY;
            }, 100);
        });
    }

    function sendToPython(manga, chapter, filename, base64Data) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "POST", url: SAVE_URL,
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify({ manga: manga, chapter: chapter, filename: filename, image_data: base64Data }),
                onload: (r) => {
                    if (r.status === 200) resolve();
                    else reject(new Error("Server Error " + r.status)); // Triggers the catch block
                },
                onerror: reject
            });
        });
    }

    function fetchImageAsBase64(url) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "GET", url: url, responseType: "blob",
                onload: function(response) {
                    if (response.status === 200) {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(response.response);
                    } else { reject(new Error(response.statusText)); }
                },
                onerror: reject
            });
        });
    }

    function goToNextChapter() {
        const titleBtn = document.querySelector('a[title="Next Chapter"]');
        if (titleBtn) { titleBtn.click(); return; }
        const selectors = ['.next_page', '.next-post', '.nav-next a', 'a.next_page'];
        for (let sel of selectors) {
            let el = document.querySelector(sel);
            if (el) { el.click(); return; }
        }
        const textToFind = ["Next", "next", "NEXT", ">"];
        for (let text of textToFind) {
            const xpath = `//a[contains(text(), '${text}')]`;
            const matchingElement = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (matchingElement) { matchingElement.click(); return; }
        }
        GM_setValue(AUTO_START_KEY, false);
        alert("❌ Couldn't find Next button.");
    }

    function getMangaTitle() {
        let el = document.querySelector('.breadcrumb li:nth-child(2) a') || document.title;
        let text = (el.innerText || el).trim();
        return text.replace(/[^a-z0-9]/gi, '_');
    }

    function getChapterTitle() {
        let pathParts = window.location.pathname.split('/');
        let name = pathParts[pathParts.length-1] || document.title;
        return name.replace(/[^a-z0-9\-]/gi, '_');
    }

    function updateStatus(msg) {
        const btns = document.querySelectorAll('button');
        if (btns.length > 0) {
             const lastBtn = btns[btns.length - 1];
             if(lastBtn.innerText !== '🛑 Stop Bridge') lastBtn.innerText = msg;
        }
    }
})();