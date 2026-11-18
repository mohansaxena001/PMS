// Progressive enhancement: occupied spots are normal links to /vehicle/<id>.
// With JS, clicking one shows a quick pop-up (data fetched from /spot/<n>,
// which reads the database) instead of navigating away.
(function () {
  const dialog = document.getElementById("spot-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  const body = document.getElementById("dlg-body");

  function row(label, value) {
    const dt = document.createElement("dt"); dt.textContent = label;
    const dd = document.createElement("dd"); dd.textContent = value;
    body.append(dt, dd);
  }

  document.querySelectorAll("a.spot.occupied").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      fetch("/spot/" + encodeURIComponent(a.dataset.spot))
        .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
        .then(function (info) {
          if (!info.vehicle) { window.location.reload(); return; }  // released elsewhere
          const v = info.vehicle;
          document.getElementById("dlg-title").textContent = "Spot " + info.spot_number;
          body.replaceChildren();
          row("Registration number", v.registration_number);
          row("Owner's name", v.owner_name);
          row("Mobile number", v.mobile_number);
          row("Assigned spot", v.spot_number);
          document.getElementById("dlg-release").href = "/vehicle/" + v.id + "/release";
          document.getElementById("dlg-manage").href = "/vehicle/" + v.id;
          dialog.showModal();
        })
        .catch(function () { window.location.href = a.href; });
    });
  });
  document.getElementById("dlg-close").addEventListener("click", function () { dialog.close(); });
})();
