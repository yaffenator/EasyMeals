from playwright.sync_api import Page, expect

def test_wizard_budget_validation(page: Page):
    # Navigate to the dashboard
    page.goto("http://localhost:3000/dashboard")
    
    # Click to open the wizard
    page.get_by_role("button", name="Create Your Meal Plan").click()
    
    # Validation: Next button should be disabled initially
    next_button = page.get_by_role("button", name="Next")
    expect(next_button).to_be_disabled()
    
    # Enter a valid budget
    page.get_by_label("Budget in USD ($)").fill("500")
    
    # Validation: Button should now be enabled
    expect(next_button).to_be_enabled()