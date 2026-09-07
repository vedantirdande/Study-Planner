document.addEventListener("DOMContentLoaded", () => {
	const themeToggle = document.querySelector("[data-theme-toggle]");
	const savedTheme = localStorage.getItem("study-portal-theme");
	const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
	const isDark = savedTheme ? savedTheme === "dark" : prefersDark;

	const updateThemeToggle = (darkMode) => {
		document.body.classList.toggle("dark-mode", darkMode);
		if (!themeToggle) return;
		themeToggle.setAttribute("aria-pressed", String(darkMode));
		themeToggle.setAttribute("aria-label", darkMode ? "Switch to light mode" : "Switch to dark mode");
		themeToggle.querySelector("[data-theme-icon]").textContent = darkMode ? "☀" : "☾";
		themeToggle.querySelector("[data-theme-label]").textContent = darkMode ? "Light mode" : "Dark mode";
	};

	updateThemeToggle(isDark);
	themeToggle?.addEventListener("click", () => {
		const darkMode = !document.body.classList.contains("dark-mode");
		localStorage.setItem("study-portal-theme", darkMode ? "dark" : "light");
		updateThemeToggle(darkMode);
	});

	const dashboard = document.querySelector("[data-dashboard]");
	if (!dashboard) return;

	const revealItems = dashboard.querySelectorAll(
		".dashboard-stats .stat-card, .card-grid .action-card, .recent-card"
	);
	revealItems.forEach((item, index) => {
		item.style.setProperty("--reveal-delay", `${Math.min(index * 55, 330)}ms`);
		item.classList.add("dashboard-reveal");
	});

	const search = dashboard.querySelector("[data-resource-search]");
	const resourceCards = [...dashboard.querySelectorAll("[data-resource-card]")];
	const resourceToggle = dashboard.querySelector("[data-resource-toggle]");
	const resourceEmpty = dashboard.querySelector("[data-resource-empty]");
	let showAll = false;

	const updateResources = () => {
		const query = (search?.value || "").trim().toLowerCase();
		const matches = resourceCards.filter((card) => card.textContent.toLowerCase().includes(query));
		resourceCards.forEach((card) => {
			const visible = matches.includes(card) && (showAll || matches.indexOf(card) < 4);
			card.hidden = !visible;
		});
		if (resourceToggle) {
			resourceToggle.hidden = matches.length <= 4;
			resourceToggle.textContent = showAll ? "Show less" : "Show more";
		}
		if (resourceEmpty) resourceEmpty.hidden = matches.length > 0 || resourceCards.length === 0;
	};

	if (search && resourceCards.length) {
		search.addEventListener("input", updateResources);
		resourceToggle?.addEventListener("click", () => {
			showAll = !showAll;
			updateResources();
		});
		updateResources();
	}
});
