from playwright.sync_api import Page, expect

def test_full_generation_flow(page: Page):
    # Start at the welcome screen
    page.goto("http://localhost:3000/dashboard")
    
    # Start Wizard
    page.get_by_role("button", name="Create Your Meal Plan").click()
    
    # Step 1: Budget
    page.get_by_label("Budget in USD ($)").fill("400")
    page.get_by_role("button", name="Next").click()
    
    # Step 2: Goal (Maintain)
    page.get_by_label("maintain Weight").click()
    page.get_by_role("button", name="Next").click()
    
    # Final Step: Finish
    # (Assuming navigation to step 5)
    page.get_by_role("button", name="Finish & Generate").click()
    
    # System Verification: Check if "Your Meal Plan" header appears
    expect(page.get_by_role("heading", name="Your Meal Plan")).to_be_visible()