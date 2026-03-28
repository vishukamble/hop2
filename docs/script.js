// Spotlight tracking
document.addEventListener('mousemove', (e) => {
    document.documentElement.style.setProperty('--x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--y', `${e.clientY}px`);
});

// OS-aware install commands
const installCommands = {
    unix: { prompt: '$', cmd: 'curl -sL https://install.hop2.tech | bash' },
    win:  { prompt: '>', cmd: 'irm https://install.hop2.tech/windows | iex' }
};

let currentOS = 'unix';

function switchOS(os) {
    currentOS = os;
    document.querySelectorAll('.os-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.os === os);
    });
    document.querySelectorAll('.install-pill .prompt').forEach(el => {
        el.textContent = installCommands[os].prompt;
    });
    document.querySelectorAll('.install-pill .cmd').forEach(el => {
        el.textContent = installCommands[os].cmd;
    });
}

function copyInstall() {
    const cmd = installCommands[currentOS].cmd;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cmd).then(() => {
            showToast("Copied to clipboard!");
        }).catch(() => {
            fallbackCopy(cmd);
        });
    } else {
        fallbackCopy(cmd);
    }
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand('copy');
        showToast("Copied to clipboard!");
    } catch {
        showToast("Press Ctrl+C to copy");
    }
    document.body.removeChild(ta);
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// Fetch latest commit from GitHub
async function initActivity() {
    const msgEl = document.getElementById('commit-message');
    if (!msgEl) return;
    try {
        const res = await fetch('https://api.github.com/repos/vishukamble/hop2/commits?per_page=1');
        const data = await res.json();
        if (data && data[0]) {
            const commitMsg = data[0].commit.message.split('\n')[0];
            msgEl.innerHTML = `<span style="color:var(--accent)">Latest Commit:</span> "${commitMsg}"`;
        }
    } catch {
        msgEl.textContent = "Check GitHub for latest updates.";
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initActivity();
});
