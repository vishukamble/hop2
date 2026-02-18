document.addEventListener('DOMContentLoaded', () => {
    initVideo();
    initCopyButtons();
    initCopyInline();
    initScrollSpy();
    initFadeUps();
    initScrollTop();
    initLatestCommit();
    updateVisitorCount();
});

// ---- VIDEO CONTROLS ----
function initVideo() {
    const video = document.getElementById('hop2-video');
    const playBtn = document.getElementById('play-pause-btn');
    const muteBtn = document.getElementById('mute-btn');
    const iconPlay = document.getElementById('icon-play');
    const iconPause = document.getElementById('icon-pause');
    const iconMute = document.getElementById('icon-mute');
    const iconSound = document.getElementById('icon-sound');

    if (!video) return;
    video.volume = 0.2;

    function updatePlayIcons() {
        iconPlay.style.display = video.paused ? '' : 'none';
        iconPause.style.display = video.paused ? 'none' : '';
    }
    function updateMuteIcons() {
        iconMute.style.display = video.muted ? '' : 'none';
        iconSound.style.display = video.muted ? 'none' : '';
    }

    playBtn?.addEventListener('click', () => {
        video.paused ? video.play() : video.pause();
        updatePlayIcons();
    });

    muteBtn?.addEventListener('click', () => {
        video.muted = !video.muted;
        updateMuteIcons();
    });

    // Autoplay/pause based on visibility
    const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) { video.play(); }
            else { video.pause(); }
            updatePlayIcons();
        });
    }, { threshold: 0.5 });

    observer.observe(video);
    updatePlayIcons();
    updateMuteIcons();
}

// ---- COPY BUTTONS (terminals) ----
function initCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const pre = btn.closest('.terminal').querySelector('pre');
            let text = pre.innerText.replace(/^\$\s*/gm, '').trim();
            try {
                await navigator.clipboard.writeText(text);
                btn.innerText = '✅';
                btn.classList.add('copied');
                setTimeout(() => { btn.innerText = '📋'; btn.classList.remove('copied'); }, 2000);
            } catch {
                btn.innerText = '❌';
                setTimeout(() => { btn.innerText = '📋'; }, 2000);
            }
        });
    });
}

// ---- COPY INLINE (install hero) ----
function initCopyInline() {
    document.querySelectorAll('.copy-inline').forEach(btn => {
        btn.addEventListener('click', async () => {
            const text = btn.dataset.copy;
            try {
                await navigator.clipboard.writeText(text);
                btn.classList.add('copied');
                btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
                setTimeout(() => {
                    btn.classList.remove('copied');
                    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
                }, 2000);
            } catch (e) { console.error(e); }
        });
    });
}

// ---- SCROLL SPY for dot nav ----
function initScrollSpy() {
    const sections = document.querySelectorAll('section[id]');
    const dots = document.querySelectorAll('.dot');

    const io = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                dots.forEach(d => {
                    d.classList.toggle('active', d.getAttribute('href') === `#${id}`);
                });
            }
        });
    }, { threshold: 0.5 });

    sections.forEach(s => io.observe(s));

    // Smooth scroll on dot click
    dots.forEach(dot => {
        dot.addEventListener('click', e => {
            e.preventDefault();
            document.querySelector(dot.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
        });
    });
}

// ---- FADE UP ANIMATIONS ----
function initFadeUps() {
    const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) e.target.classList.add('visible');
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.section-header, .cards-grid, .terminal-grid, .steps, .community-grid, .install-hero').forEach(el => {
        el.classList.add('fade-up');
        io.observe(el);
    });
}

// ---- SCROLL TO TOP ----
function initScrollTop() {
    const btn = document.getElementById('scrollTop');
    window.addEventListener('scroll', () => {
        btn?.classList.toggle('visible', window.scrollY > window.innerHeight * 0.4);
    });
    btn?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ---- LATEST COMMIT ----
function initLatestCommit() {
    const msgEl = document.getElementById('commit-message');
    const linkEl = document.getElementById('commit-link');
    fetch('https://api.github.com/repos/vishukamble/hop2/commits?per_page=1')
        .then(r => r.json())
        .then(data => {
            if (data?.[0]) {
                const msg = data[0].commit.message.split('\n')[0];
                msgEl.textContent = `Latest commit: "${msg}"`;
                linkEl.href = data[0].html_url;
            } else {
                msgEl.textContent = 'View on GitHub ↗';
            }
        })
        .catch(() => { msgEl.textContent = 'View on GitHub ↗'; });
}

// ---- VISITOR COUNT ----
function updateVisitorCount() {
    fetch('https://api.counterapi.dev/v1/hop2-website/count/up')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('visitor-count');
            if (el && data?.count) el.innerText = data.count.toLocaleString('en-US');
        })
        .catch(() => {
            const el = document.getElementById('visitor-count');
            if (el) el.innerText = 'N/A';
        });
}