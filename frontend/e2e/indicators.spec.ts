import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

// Manager opens the monthly detail of the indicators and downloads the PDF reports (annual and monthly).
test("monthly detail and PDF report", async ({ page }) => {
  const year = new Date().getFullYear();
  await page.goto("/");
  await page.getByLabel("Identifiant").fill("resp");
  await page.getByLabel("Mot de passe").fill("demo-2026");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("link", { name: "Tableau de bord" }).click();

  const detail = page.locator("section.month-detail");
  await expect(detail.getByRole("heading", { name: "Détail du mois" })).toBeVisible();

  // Pick January from the month strip
  await detail.getByRole("radio", { name: `Janvier ${year}` }).click();
  await expect(detail.getByRole("heading", { name: `Janvier ${year}` })).toBeVisible();
  await expect(detail.getByRole("button", { name: "Mois précédent" })).toBeDisabled();
  await expect(detail.locator("table.month-kpis tbody tr")).toHaveCount(10);
  await expect(detail.getByRole("heading", { name: "Eau et pertes" })).toBeVisible();

  // Next month with the arrow
  await detail.getByRole("button", { name: "Mois suivant" }).click();
  await expect(detail.getByRole("heading", { name: `Février ${year}` })).toBeVisible();

  // Month header in the monthly table opens the same detail
  await page.getByRole("button", { name: "Détail de Mars" }).click();
  await expect(detail.getByRole("heading", { name: `Mars ${year}` })).toBeVisible();

  // Monthly PDF
  const [monthly] = await Promise.all([page.waitForEvent("download"), detail.getByRole("button", { name: "PDF du mois" }).click()]);
  expect(monthly.suggestedFilename()).toBe(`ymejibu_indicateurs_${year}-03.pdf`);
  expect(readFileSync((await monthly.path())!).subarray(0, 5).toString()).toBe("%PDF-");

  // Full annual report
  const [annual] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /Rapport PDF/ }).click()]);
  expect(annual.suggestedFilename()).toBe(`ymejibu_indicateurs_${year}.pdf`);
  expect(readFileSync((await annual.path())!).length).toBeGreaterThan(20_000);
});
