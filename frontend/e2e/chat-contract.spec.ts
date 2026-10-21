import { test, expect, type Page } from '@playwright/test'
import { STREAMS } from './fixtures/contractStreams'

const LIVE = process.env.E2E_LIVE_BACKEND === '1'

async function mockSupportApis(page: Page) {
  await page.route('**/api/anon-session**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user_id: 'e2e-user', token: null }),
    })
  })
  await page.route('**/api/config**', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Config unavailable' }),
    })
  })
  await page.route('**/api/profile**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'e2e-user',
        dietary_preference: 'No rules',
        allergens: [],
        lifestyle: [],
      }),
    })
  })
}

async function mockChat(page: Page, body: string, status = 200) {
  await page.route('**/api/chat**', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback()
      return
    }
    if (status !== 200) {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Backend Error', detail: `status ${status}` }),
      })
      return
    }
    await route.fulfill({ status: 200, contentType: 'text/plain', body })
  })
}

async function openChat(page: Page) {
  await page.goto('/chat')
  const input = page.getByTestId('chat-input')
  await expect(input).toBeEnabled({ timeout: 15_000 })
  return input
}

async function send(page: Page, text: string) {
  const input = page.getByTestId('chat-input')
  await input.fill(text)
  await page.getByRole('button', { name: 'Send' }).click()
}

async function dismissOnboarding(page: Page) {
  const close = page.getByRole('button', { name: 'Close' })
  if (await close.isVisible().catch(() => false)) {
    await close.click()
  }
}

test.describe('chat contract states', () => {
  test.beforeEach(async ({ page }) => {
    await mockSupportApis(page)
  })

  test('profile required: notice, no verdict chips', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.profileRequired)
    const input = await openChat(page)
    await send(page, 'Ingredients: water, salt.')
    await expect(page.getByTestId('profile-required-notice')).toBeVisible({ timeout: 15_000 })
    await dismissOnboarding(page)
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
    await expect(input).toBeEnabled()
  })

  test('lactose confirm shows echo, avoid, and yes/no/only-today', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.lactoseConfirm)
    await openChat(page)
    await send(page, "I'm lactose intolerant. Milk, sugar.")
    await expect(page.getByTestId('understanding-echo')).toContainText('I understood')
    await expect(page.getByTestId('understanding-echo')).toContainText('dairy-free')
    await expect(page.getByTestId('confirm-restriction-actions')).toBeVisible()
    await expect(page.getByTestId('confirm-yes')).toBeVisible()
    await expect(page.getByTestId('confirm-no')).toBeVisible()
    await expect(page.getByTestId('confirm-only-today')).toBeVisible()
  })

  test('confirm yes persists', async ({ page }) => {
    if (!LIVE) {
      let turn = 0
      await page.route('**/api/chat**', async (route) => {
        if (route.request().method() !== 'POST') return route.fallback()
        turn += 1
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: turn === 1 ? STREAMS.lactoseConfirm : STREAMS.confirmYes,
        })
      })
    }
    await openChat(page)
    await send(page, "I'm lactose intolerant.")
    await expect(page.getByTestId('confirm-yes')).toBeVisible()
    await page.getByTestId('confirm-yes').click()
    await expect(page.getByText(/Saved on your profile/i)).toBeVisible()
  })

  test('confirm no drops pending', async ({ page }) => {
    if (!LIVE) {
      let turn = 0
      await page.route('**/api/chat**', async (route) => {
        if (route.request().method() !== 'POST') return route.fallback()
        turn += 1
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: turn === 1 ? STREAMS.lactoseConfirm : STREAMS.confirmNo,
        })
      })
    }
    await openChat(page)
    await send(page, "I'm lactose intolerant.")
    await page.getByTestId('confirm-no').click()
    await expect(page.getByText(/won't save that restriction/i)).toBeVisible()
  })

  test('confirm only today stays session-only', async ({ page }) => {
    if (!LIVE) {
      let turn = 0
      await page.route('**/api/chat**', async (route) => {
        if (route.request().method() !== 'POST') return route.fallback()
        turn += 1
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: turn === 1 ? STREAMS.lactoseConfirm : STREAMS.confirmOnlyToday,
        })
      })
    }
    await openChat(page)
    await send(page, "I'm lactose intolerant.")
    await page.getByTestId('confirm-only-today').click()
    await expect(page.getByText(/this session only/i)).toBeVisible()
  })

  test('emergency unknown locale shows generic list, no verdict', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'language', { get: () => 'en' })
    })
    if (!LIVE) await mockChat(page, STREAMS.emergencyGeneric)
    await openChat(page)
    await send(page, 'Call emergency. Ingredients: water.')
    await expect(page.getByTestId('emergency-block')).toBeVisible()
    await expect(page.getByTestId('emergency-generic-list')).toBeVisible()
    await expect(page.getByTestId('emergency-generic-list')).toContainText('911')
    await expect(page.getByTestId('emergency-generic-list')).toContainText('999')
    await expect(page.getByTestId('emergency-generic-list')).toContainText('112')
    await expect(page.getByTestId('emergency-generic-list')).toContainText('000')
    await expect(page.getByTestId('emergency-generic-list')).toContainText('111')
    await expect(page.getByTestId('emergency-generic-list')).toContainText('998')
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
  })

  test('emergency US locale shows 911', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'language', { get: () => 'en-US' })
    })
    if (!LIVE) await mockChat(page, STREAMS.emergencyGeneric)
    await openChat(page)
    await send(page, "I can't breathe after peanuts.")
    await expect(page.getByTestId('emergency-block')).toBeVisible()
    await expect(page.getByTestId('emergency-block')).toContainText('911')
    await expect(page.getByTestId('emergency-generic-list')).toHaveCount(0)
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
  })

  test('emergency UK locale shows 999', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'language', { get: () => 'en-GB' })
    })
    if (!LIVE) await mockChat(page, STREAMS.emergencyGeneric)
    await openChat(page)
    await send(page, 'Call 999. Ingredients: water.')
    await expect(page.getByTestId('emergency-block')).toContainText('999')
  })

  test('emergency India locale shows 112', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'language', { get: () => 'en-IN' })
    })
    if (!LIVE) await mockChat(page, STREAMS.emergencyGeneric)
    await openChat(page)
    await send(page, 'Call emergency.')
    await expect(page.getByTestId('emergency-block')).toContainText('112')
  })

  test('product-name question does not show SAFE', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.productName)
    await openChat(page)
    await send(page, 'Can I eat this Oreo?')
    await expect(page.getByText(/ingredient list from the pack/i)).toBeVisible()
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
    await expect(page.getByText(/will not mark this SAFE from the name alone/i)).toBeVisible()
  })

  test('bilingual label shows one echo, not multi-product', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.bilingual)
    await openChat(page)
    await send(
      page,
      'Ingredients: Sugar, milk. Ingredients (FR): Sucre, lait. Zutaten: Zucker, Milch',
    )
    await expect(page.getByTestId('understanding-echo')).toBeVisible()
    await expect(page.getByText(/more than one product/i)).toHaveCount(0)
  })

  test('multi-product refuses a combined verdict', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.multiProduct)
    await openChat(page)
    await send(page, 'Product A: water, sugar. Product B: milk, salt.')
    await expect(page.getByText(/more than one product/i)).toBeVisible()
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
  })

  test('unsupported restriction (keto)', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.unsupported)
    await openChat(page)
    await send(page, "I'm keto.")
    await expect(page.getByText(/don't evaluate keto/i)).toBeVisible()
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
  })

  test('degraded fail-closed: no verdict chips', async ({ page }) => {
    if (!LIVE) await mockChat(page, STREAMS.degraded)
    await openChat(page)
    await send(page, 'Ingredients: water.')
    await expect(page.getByTestId('degraded-notice')).toBeVisible()
    await expect(page.getByTestId('verdict-chips')).toHaveCount(0)
  })

  test('HTTP 413', async ({ page }) => {
    await mockChat(page, '', 413)
    await openChat(page)
    await send(page, 'Ingredients: water.')
    await expect(page.getByText(/too large/i)).toBeVisible()
  })

  test('HTTP 422', async ({ page }) => {
    await mockChat(page, '', 422)
    await openChat(page)
    await send(page, 'Ingredients: water.')
    await expect(page.getByText(/could not be processed/i)).toBeVisible()
  })

  test('HTTP 429', async ({ page }) => {
    await mockChat(page, '', 429)
    await openChat(page)
    await send(page, 'Ingredients: water.')
    await expect(page.getByText(/too many requests/i)).toBeVisible()
  })
})
