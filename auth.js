/* ============================================
   Password Protection for Ziyue (Brian) Wang's Website

   HOW TO CHANGE THE PASSWORD:
   Edit the value in the line below.

   HOW TO REMOVE PASSWORD PROTECTION:
   1. Delete the <div class="password-gate">...</div> block from each HTML file
   2. Change <div class="site-content"> to just the page content without the wrapper
   3. Remove the <script src="auth.js"></script> line from each page
   Or simply delete this file and remove references to it.
   ============================================ */

const SITE_PASSWORD = '666593';

function checkAuth() {
    return sessionStorage.getItem('site_auth') === 'true';
}

function unlock() {
    sessionStorage.setItem('site_auth', 'true');
    document.querySelector('.password-gate').style.display = 'none';
    document.querySelector('.site-content').classList.add('unlocked');
}

function tryPassword() {
    const input = document.getElementById('pwd-input');
    const errorMsg = document.getElementById('pwd-error');

    if (input.value === SITE_PASSWORD) {
        unlock();
    } else {
        input.classList.add('error');
        errorMsg.style.display = 'block';
        setTimeout(() => {
            input.classList.remove('error');
        }, 400);
    }
}

// Run on page load
document.addEventListener('DOMContentLoaded', function() {
    if (checkAuth()) {
        unlock();
    }

    // Allow Enter key to submit
    const input = document.getElementById('pwd-input');
    if (input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') tryPassword();
        });
    }
});
