// Custom cursor functionality
document.addEventListener('DOMContentLoaded', () => {
    initializeCustomCursor();
    initializeAnimations();
    initializeSmoothScroll();
    initializeTerminalEffects();
    initializeParallax();
    initializeCopyButtons();
    initializeDotNavigation();
    initializeLatestCommit();
    initializeScrollToTop();
    updateVisitorCount();
});

function initializeCustomCursor() {
    const cursor = document.querySelector('.custom-cursor');

    document.addEventListener('mousemove', e => {
        document.documentElement.style.setProperty(
            '--cursor-translate',
            `translate(${e.clientX}px, ${e.clientY}px)`
        );
    });

    // Hover effects
    const links = document.querySelectorAll('a, button');
    links.forEach(link => {
        link.addEventListener('mouseenter', () =>
            cursor.classList.add('cursor--big')
        );
        link.addEventListener('mouseleave', () =>
            cursor.classList.remove('cursor--big')
        );
    });
}

function initializeAnimations() {
    // Fade in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });
}

function initializeSmoothScroll() {
    // Smooth scroll for navigation (excluding scroll-to-top button)
    document.querySelectorAll('a[href^="#"]:not(.scroll-to-top)').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({behavior: 'smooth'});
            }
        });
    });
}

function initializeTerminalEffects() {
    // Terminal typing effect
    const terminals = document.querySelectorAll('.terminal pre');
    terminals.forEach(terminal => {
        const originalText = terminal.innerHTML;
        terminal.style.opacity = '0';

        const terminalObserver = new IntersectionObserver(function (entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    terminal.style.opacity = '1';
                    terminal.style.transition = 'opacity 0.5s ease';
                    terminalObserver.unobserve(terminal);
                }
            });
        }, {threshold: 0.5});

        terminalObserver.observe(terminal);
    });
}

function initializeParallax() {
    // Parallax effect for hero
    let ticking = false;

    function updateParallax() {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.hero');
        const logo = document.querySelector('.logo');

        if (scrolled < window.innerHeight) {
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
            logo.style.transform = `translateY(${scrolled * -0.3}px) rotate(${scrolled * 0.1}deg)`;
        }

        ticking = false;
    }

    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(updateParallax);
            ticking = true;
        }
    });
}

function initializeCopyButtons() {
    // Copy button functionality
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const pre = button.closest('.terminal').querySelector('pre');
            let text = pre.innerText;

            // Remove leading '$' and whitespace
            text = text.replace(/^\$\s*/, '');

            try {
                await navigator.clipboard.writeText(text);

                button.innerText = '✅';
                button.classList.add('copied');
                setTimeout(() => {
                    button.innerText = '📋';
                    button.classList.remove('copied');
                }, 2000);
            } catch (err) {
                console.error('Error copying text to clipboard:', err);
                button.innerText = '❌';
                setTimeout(() => {
                    button.innerText = '📋';
                }, 2000);
            }
        });
    });
}

function initializeDotNavigation() {
    // Dot Navigation (Scrollspy)
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.dot-nav a');

    const navObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.getAttribute('id');
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${id}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, {threshold: 0.5});

    sections.forEach(section => navObserver.observe(section));
}

function initializeLatestCommit() {
    // Latest Commit Loader
    const msgEl = document.getElementById('commit-message');
    const linkEl = document.getElementById('commit-link');

    fetch('https://api.github.com/repos/vishukamble/hop2/commits?per_page=1')
        .then(res => res.json())
        .then(data => {
            if (data && data.length > 0) {
                const commit = data[0];
                const commitMessage = commit.commit.message.split('\n')[0]; // Get first line of message
                msgEl.textContent = `Latest: "${commitMessage}"`;
                linkEl.href = commit.html_url;
            } else {
                msgEl.textContent = 'Could not load latest activity.';
            }
        })
        .catch(() => {
            msgEl.textContent = 'Could not load latest activity.';
        });
}

function initializeScrollToTop() {
    const scrollToTopButton = document.querySelector('.scroll-to-top');
    const root = document.documentElement; // Get the <html> element

    window.addEventListener('scroll', () => {
        if (window.scrollY > window.innerHeight / 2) {
            scrollToTopButton.classList.add('visible');
        } else {
            scrollToTopButton.classList.remove('visible');
        }
    });

    scrollToTopButton.addEventListener('click', (e) => {
        e.preventDefault();

        root.style.scrollSnapType = 'none';

        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });

        let scrollTimeout;
        const scrollListener = () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                root.style.scrollSnapType = 'y mandatory';
                window.removeEventListener('scroll', scrollListener);
            }, 100);
        };
        window.addEventListener('scroll', scrollListener);
    });
}

function updateVisitorCount() {
    const namespace = 'hop2-website';
    const key = 'count';

    fetch(`https://api.counterapi.dev/v1/${namespace}/${key}/up`)
        .then(res => res.json())
        .then(data => {
            const countElement = document.getElementById('visitor-count');
            if (countElement) {
                countElement.innerText = data.count.toLocaleString('en-US');
            }
        })
        .catch(error => {
            console.error("Visitor count failed:", error);
            const countElement = document.getElementById('visitor-count');
            if (countElement) {
                countElement.innerText = 'N/A';
            }
        });
}

// Wait for the document to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('hop2-video');
    // Mute button elements
    const muteBtn = document.getElementById('mute-btn');
    const muteIcon = document.getElementById('mute-icon');
    // Play/Pause button elements
    const playPauseBtn = document.getElementById('play-pause-btn');
    const playPauseIcon = document.getElementById('play-pause-icon');
    // --- Define Icon Paths ---
    const volumeOnIconPath = 'assets/img/unmute.svg';
    const volumeOffIconPath = 'assets/img/mute.svg';
    const playIconPath = 'assets/img/play.svg';
    const pauseIconPath = 'assets/img/pause.svg';

    if (video) {
        video.volume = 0.2; // Set default volume to 20%
    }

    // Mute/Unmute Logic
    if (muteBtn) {
        muteBtn.addEventListener('click', () => {
            video.muted = !video.muted;
            muteIcon.src = video.muted ? volumeOffIconPath : volumeOnIconPath;
        });
    }

    // Play/Pause Logic
    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', () => {
            if (video.paused) {
                video.play();
                playPauseIcon.src = pauseIconPath;
            } else {
                video.pause();
                playPauseIcon.src = playIconPath;
            }
        });
    }
});
