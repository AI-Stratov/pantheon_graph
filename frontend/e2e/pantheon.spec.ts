import { expect, type Page, test } from '@playwright/test';

const isMobile = (page: Page) => (page.viewportSize()?.width ?? 0) < 760;

async function pick(page: Page, testid: string, query: string, option: string) {
  const input = page.getByTestId(testid);
  await input.fill(query);
  await page.getByRole('option', { name: new RegExp(`^.? ?${option}`) }).first().click();
}

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (error) => {
    throw error;
  });
});

test('opens on the map of the pantheon', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Pantheon', level: 1 })).toBeVisible();
  await expect(page.locator('canvas').first()).toBeVisible();
  await expect(page.getByRole('radio', { name: 'Constellation' })).toHaveAttribute('aria-checked', 'true');
});

test('the oracle names a relationship', async ({ page }) => {
  await page.goto('/');
  if (isMobile(page)) await page.getByRole('button', { name: 'How are they related?' }).click();
  await pick(page, 'ask-from', 'hera', 'Heracles');
  await pick(page, 'ask-to', 'uran', 'Uranus');
  await page.getByRole('button', { name: 'Reveal' }).click();

  await expect(page.getByTestId('kinship')).toHaveText('Heracles is the great-grandson of Uranus');
  await expect(page.getByTestId('connection-card').getByRole('listitem')).toHaveCount(7);
  await expect(page).toHaveURL(/\?from=heracles&to=uranus$/);
});

test('reverse turns the sentence around', async ({ page }) => {
  await page.goto('/?from=hephaestus&to=zeus');
  await expect(page.getByTestId('kinship')).toHaveText('Hephaestus is the stepson of Zeus');
  await page.getByRole('button', { name: 'Reverse' }).click();
  await expect(page.getByTestId('kinship')).toHaveText('Zeus is the stepfather of Hephaestus');
});

test('search opens a deity and relatives are navigable', async ({ page }) => {
  await page.goto('/');
  await pick(page, 'search', 'athe', 'Athena');

  const card = page.getByTestId('deity-card');
  await expect(card.getByRole('heading', { name: 'Athena', level: 2 })).toBeVisible();
  await expect(card).toContainText('Ἀθηνᾶ');
  await expect(page).toHaveURL(/\?node=athena$/);

  await card.getByRole('button', { name: 'Metis' }).click();
  await expect(page.getByTestId('deity-card').getByRole('heading', { name: 'Metis', level: 2 })).toBeVisible();
});

test('a deity card can start a connection', async ({ page }) => {
  await page.goto('/?node=athena');
  await pick(page, 'relate-to', 'hades', 'Hades');
  await expect(page.getByTestId('kinship')).toHaveText('Athena is the niece of Hades');
});

test('deep links restore the view and escape clears it', async ({ page }) => {
  await page.goto('/?layout=tree&node=zeus');
  await expect(page.getByTestId('deity-card').getByRole('heading', { name: 'Zeus', level: 2 })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page.getByTestId('deity-card')).toBeHidden();
  await expect(page).toHaveURL(/\?layout=tree$/);
  // On phones the layout switch shares the bottom of the screen with the open card
  await expect(page.getByRole('radio', { name: 'Family tree' })).toHaveAttribute('aria-checked', 'true');
});

test('separate lineages are reported, not hidden', async ({ page }) => {
  await page.goto('/?from=eris&to=zeus');
  await expect(page.getByTestId('connection-card')).toContainText('are not related');
});

/** Counts camera animations started on the Cytoscape core behind the canvas. */
async function watchCamera(page: Page) {
  await page.waitForFunction(() => document.querySelector('.canvas canvas'));
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    type Core = { animate: (...args: unknown[]) => unknown };
    const holder = document.querySelector('.canvas') as unknown as { _cyreg: { cy: Core } };
    const cy = holder._cyreg.cy;
    const w = window as unknown as { cameraMoves: number };
    w.cameraMoves = 0;
    const animate = cy.animate.bind(cy);
    cy.animate = (...args: unknown[]) => {
      w.cameraMoves += 1;
      return animate(...args);
    };
  });
  return {
    moves: () => page.evaluate(() => (window as unknown as { cameraMoves: number }).cameraMoves),
  };
}

test('one selection moves the camera once', async ({ page }) => {
  await page.goto('/');
  const camera = await watchCamera(page);

  await pick(page, 'search', 'athe', 'Athena');
  await expect(page.getByTestId('deity-card')).toBeVisible();
  await page.waitForTimeout(800);
  expect(await camera.moves()).toBe(1);

  await page.getByTestId('deity-card').getByRole('button', { name: 'Metis' }).click();
  await page.waitForTimeout(800);
  expect(await camera.moves()).toBe(2);

  await page.keyboard.press('Escape');
  await page.waitForTimeout(800);
  expect(await camera.moves()).toBe(3);
});

test('the constellation keeps medallions and names apart', async ({ page }) => {
  await page.goto('/');
  await page.waitForFunction(() => document.querySelector('.canvas canvas'));
  await page.waitForTimeout(400);
  const collisions = await page.evaluate(() => {
    type Box = { x1: number; x2: number; y1: number; y2: number };
    type Node = { id: () => string; boundingBox: (options: object) => Box };
    const holder = document.querySelector('.canvas') as unknown as { _cyreg: { cy: { nodes: () => Node[] } } };
    const boxes = [...holder._cyreg.cy.nodes()].map((node) => ({ id: node.id(), box: node.boundingBox({ includeLabels: true }) }));
    const hits: string[] = [];
    boxes.forEach((a, i) =>
      boxes.slice(i + 1).forEach((b) => {
        if (a.box.x1 < b.box.x2 && b.box.x1 < a.box.x2 && a.box.y1 < b.box.y2 && b.box.y1 < a.box.y2) hits.push(`${a.id}/${b.id}`);
      }),
    );
    return hits;
  });
  expect(collisions).toEqual([]);
});

test('relatives are tagged with their role', async ({ page }) => {
  await page.goto('/?node=cronus');
  const roles = page.locator('.roles span');
  await expect(roles).toHaveCount(9); // 2 parents, 1 consort, 6 children
  await expect(roles.filter({ hasText: 'wife' })).toHaveCount(1);
  await expect(roles.filter({ hasText: 'daughter' })).toHaveCount(3);

  await page.keyboard.press('Escape');
  await expect(roles).toHaveCount(0);
});
