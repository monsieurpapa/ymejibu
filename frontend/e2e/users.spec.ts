import { expect, test } from "@playwright/test";

// Super administrator manages accounts from the dashboard: create, edit role, reset password, deactivate, delete.
test("super admin manages users and roles", async ({ page, browser }) => {
  await page.goto("/");
  await page.getByLabel("Identifiant").fill("superadmin");
  await page.getByLabel("Mot de passe").fill("Goma-Ouest-2026!");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("link", { name: "Tableau de bord" }).click();
  await page.getByRole("link", { name: "Utilisateurs" }).click();
  await expect(page.getByRole("heading", { name: "Utilisateurs et accès" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rôles et droits" })).toBeVisible();

  // Create
  await page.getByRole("button", { name: "Nouvel utilisateur" }).click();
  const dlg = page.getByRole("dialog");
  await dlg.getByLabel("Identifiant").fill("agent.test");
  await dlg.getByLabel("Nom complet").fill("Agent Test");
  await dlg.getByLabel(/^Rôle/).selectOption("ZONE_TECH");
  await expect(dlg.getByText(/Saisit :/)).toBeVisible();
  await dlg.getByLabel(/^Zone/).selectOption({ index: 1 });
  await dlg.getByLabel("Mot de passe", { exact: false }).first().fill("12345678");
  await dlg.getByRole("button", { name: "Créer le compte" }).click();
  await expect(dlg.getByRole("alert").first()).toBeVisible(); // numeric password refused
  await dlg.locator("#u-password").fill("Terrain-Goma-2026");
  await dlg.getByRole("button", { name: "Créer le compte" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const row = page.locator(".user-row", { hasText: "@agent.test" });
  await expect(row).toContainText("Technicien de zone");

  // The new account can sign in
  const other = await browser.newPage();
  await other.goto("/");
  await other.getByLabel("Identifiant").fill("agent.test");
  await other.getByLabel("Mot de passe").fill("Terrain-Goma-2026");
  await other.getByRole("button", { name: "Se connecter" }).click();
  await expect(other.getByRole("heading", { name: "Nouvelle fiche" })).toBeVisible();
  await other.close();

  // Edit role
  await row.getByRole("button", { name: "Modifier" }).click();
  await page.getByRole("dialog").getByLabel(/^Rôle/).selectOption("PUMP_FOCAL");
  await page.getByRole("dialog").getByRole("button", { name: "Enregistrer" }).click();
  await expect(row).toContainText("Point focal pompage");

  // Reset password
  await row.getByRole("button", { name: "Mot de passe" }).click();
  await page.locator("#u-password").fill("Pompage-Goma-2026");
  await page.getByRole("button", { name: "Définir le mot de passe" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // Deactivate then delete
  await row.getByRole("button", { name: "Désactiver" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Désactiver" }).click();
  await expect(row).toContainText("Désactivé");
  await row.getByRole("button", { name: "Supprimer" }).click();
  await page.getByRole("button", { name: "Supprimer définitivement" }).click();
  await expect(page.locator(".user-row", { hasText: "@agent.test" })).toHaveCount(0);

  // Own account is protected
  const mine = page.locator(".user-row", { hasText: "@superadmin" });
  await expect(mine.getByRole("button", { name: "Supprimer" })).toBeDisabled();
});
