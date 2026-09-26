/**
 * End-to-end: a pump operator fills a daily pumping log and an incident report
 * with NO connection on a phone-sized screen, comes back online, the outbox
 * syncs, and the manager's dashboard shows the new August figures.
 */
import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "demo-2026";
const byId = (page: Page, id: string) => page.locator(`[id="${id}"]`);

async function login(page: Page, username: string) {
  await page.goto("/");
  await page.getByLabel("Identifiant").fill(username);
  await page.getByLabel("Mot de passe").fill(PASSWORD);
  await page.getByRole("button", { name: "Se connecter" }).click();
}

async function augustCell(page: Page, rowLabel: string) {
  const row = page.locator("table.data tr", { has: page.getByRole("rowheader", { name: rowLabel, exact: true }) });
  return row.locator("td").nth(7); // Janvier = 0 … Août = 7
}

test("offline pumping log + incident, then sync updates August KPIs", async ({ browser }) => {
  // --- Manager: August has no pumping data yet.
  const managerCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const manager = await managerCtx.newPage();
  await login(manager, "resp");
  await manager.getByRole("link", { name: "Tableau de bord" }).click();
  await expect(manager.getByRole("heading", { name: /Tableau de bord E&M/ })).toBeVisible();
  await expect(await augustCell(manager, "Eau introduite")).toHaveText("");
  await expect(await augustCell(manager, "Pannes signalées")).toHaveText("");

  // --- Operator on a phone: log in while online, the app caches itself and the reference data.
  const phoneCtx = await browser.newContext({ ...test.info().project.use, serviceWorkers: "allow" });
  const phone = await phoneCtx.newPage();
  await login(phone, "pompage");
  await expect(phone.getByRole("heading", { name: "Nouvelle fiche" })).toBeVisible();
  await phone.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await phone.reload();
  await expect(phone.getByRole("heading", { name: "Nouvelle fiche" })).toBeVisible();

  // --- Connection lost. The app still opens (service worker) and knows it is offline.
  await phoneCtx.setOffline(true);
  await phone.reload();
  await expect(phone.getByTestId("syncbar")).toContainText("Hors ligne");
  await expect(phone.getByRole("heading", { name: "Nouvelle fiche" })).toBeVisible();

  // Daily pumping log: CAPRARI 06:00-10:00 at 180 m³/h -> 720 m³.
  await phone.getByRole("button", { name: /Station de pompage/ }).click();
  await byId(phone, "general.station").selectOption("GO-STP-001");
  await byId(phone, "general.date").fill("2026-08-10");
  await byId(phone, "general.operator").fill("Opérateur E2E");
  await byId(phone, "pumps[0].pump").selectOption("GO-PMP-001");
  await byId(phone, "pumps[0].start").fill("06:00");
  await byId(phone, "pumps[0].stop").fill("10:00");
  await byId(phone, "pumps[0].flow_m3h").fill("180");
  await byId(phone, "energy.snel.quantity").fill("150");
  await byId(phone, "quality.residual_chlorine.value").fill("0.6");
  await expect(byId(phone, "quality.residual_chlorine.conforme")).toHaveText(/Oui/);
  await phone.getByTestId("submit").click();
  await expect(phone.getByTestId("queued-count")).toHaveText("1 en attente");

  // Incident report with a photo and 3 h of service interruption.
  await phone.getByRole("button", { name: "Formulaire de rapport de panne" }).click();
  await byId(phone, "general.date").fill("2026-08-10");
  await byId(phone, "general.detected_time").fill("07:30");
  await byId(phone, "general.node").selectOption("1.10");
  await byId(phone, "description.incident_type").selectOption("RUPTURE");
  await byId(phone, "description.severity").getByRole("radio", { name: "Critique" }).click();
  await byId(phone, "description.service_interrupted").getByRole("radio", { name: "Oui" }).click();
  await byId(phone, "description.downtime_cause").selectOption("PIPE_BURST");
  await byId(phone, "description.downtime_hours").fill("3");
  await phone.locator('input[type="file"]').setInputFiles({
    name: "fuite.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVR4nGP8z8DwnwEIGBmBAAAWfQH/Z5N7sAAAAABJRU5ErkJggg==",
      "base64",
    ),
  });
  await expect(phone.getByRole("img", { name: "Photo 1" })).toBeVisible();
  await byId(phone, "analysis.probable_cause").selectOption("VANDALISM");
  await byId(phone, "intervention.maintenance_type").getByRole("radio", { name: /Urgente/ }).click();
  await phone.getByTestId("submit").click();
  await expect(phone.getByTestId("queued-count")).toHaveText("2 en attente");
  await expect(phone.getByText("En attente d'envoi")).toHaveCount(2);

  // Still offline after a reload: nothing is lost.
  await phone.reload();
  await expect(phone.getByTestId("queued-count")).toHaveText("2 en attente");

  // --- Connection is back: the outbox empties by itself.
  await phoneCtx.setOffline(false);
  await phone.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(phone.getByTestId("queued-count")).toHaveText("0 en attente", { timeout: 30_000 });
  await expect(phone.getByText("Envoyée")).toHaveCount(2);
  // The incident received its server number.
  await phone.getByRole("link", { name: /rapport de panne/i }).click();
  await expect(phone.getByText(/GO-INC-2026-\d{4}/).first()).toBeVisible();

  // --- Manager: August now shows the new data.
  await manager.getByRole("button", { name: "Actualiser" }).click();
  await expect(await augustCell(manager, "Eau introduite")).toHaveText("720 m³");
  await expect(await augustCell(manager, "Pannes signalées")).toHaveText("1");
  await expect(await augustCell(manager, "Heures d'arrêt")).toHaveText("3 h");
  await expect(await augustCell(manager, "Disponibilité")).toHaveText(/99,6/);
  // The new sheets wait for the manager's review.
  await manager.getByRole("link", { name: /^Fiches/ }).click();
  await expect(manager.getByRole("button", { name: /Rapport de panne/ })).toBeVisible();

  await managerCtx.close();
  await phoneCtx.close();
});
