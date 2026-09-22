const form = document.getElementById("aiForm");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = document.getElementById("aiInput").value.trim();
    const box = document.getElementById("aiResults");
    if (!q) return;
    box.innerHTML = "<p>Finding the best matches...</p>";
    const res = await fetch("/api/recommend?q=" + encodeURIComponent(q));
    const products = await res.json();
    box.innerHTML = products.map(p =>
      `<div class="ai-result"><strong>${p.name}</strong> — ₹${p.sale_price} &nbsp; ★ ${p.rating}
       <a href="/product/${p.id}" style="float:right;font-weight:800">View →</a></div>`
    ).join("");
  });
}
