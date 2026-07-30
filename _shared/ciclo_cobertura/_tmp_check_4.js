
        function toggleMobileNav() { const p = document.getElementById('mobilePanel'), i = document.getElementById('togglerIcon'); p.classList.toggle('open'); i.className = p.classList.contains('open') ? 'fas fa-times' : 'fas fa-bars'; }
        function closeMobileNav() { document.getElementById('mobilePanel').classList.remove('open'); document.getElementById('togglerIcon').className = 'fas fa-bars'; }
        document.addEventListener('click', function (e) { const p = document.getElementById('mobilePanel'), t = document.getElementById('navToggler'); if (p.classList.contains('open') && !p.contains(e.target) && !t.contains(e.target)) closeMobileNav(); });
    