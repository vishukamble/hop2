document.addEventListener('mousemove', (e) => {
    // Spotlight Tracking
    document.documentElement.style.setProperty('--x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--y', `${e.clientY}px`);
});

function copyInstall() {
    const cmd = "curl -sL https://install.hop2.tech | bash";
    navigator.clipboard.writeText(cmd).then(() => {
        showToast("Installation command copied!");
    });
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// Fetch GitHub Activity
async function initActivity() {
    const msgEl = document.getElementById('commit-message');
    try {
        const res = await fetch('https://api.github.com/repos/vishukamble/hop2/commits?per_page=1');
        const data = await res.json();
        if (data && data[0]) {
            const commitMsg = data[0].commit.message.split('\n')[0];
            msgEl.innerHTML = `<span style="color:var(--accent)">Latest Commit:</span> "${commitMsg}"`;
        }
    } catch (e) {
        msgEl.textContent = "Check GitHub for latest updates.";
    }
}

// Fetch Visitor Count
function initCounter() {
    const namespace = 'hop2-website';
    const key = 'count';
    const el = document.getElementById('visitor-count');
    
    fetch(`https://api.counterapi.dev/v1/${namespace}/${key}/up`)
        .then(res => res.json())
        .then(data => {
            if (el) el.innerText = data.count.toLocaleString();
        })
        .catch(() => { if (el) el.innerText = "1,000+"; });
}

document.addEventListener('DOMContentLoaded', () => {
    initActivity();
    initCounter();
});