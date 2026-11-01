
from ai_service import generate_reply
import time

# ==========================================
# Test Executive Identity
# ==========================================

identity = {
    "name": "Judy",
    "job_title": "Founder & CEO",
    "company_name": "DisruptEverything AI",
    "industry": "Artificial Intelligence",
    "valuation": "$50 billion",
    "net_worth": "$8 billion",
    "biography": (
        "A visionary serial entrepreneur who has "
        "revolutionized multiple industries."
    )
}

# ==========================================
# Test Emails
# ==========================================

test_emails = {
    "interview": """
Hi Judy,

We'd love to invite you to a 15-minute interview
for a software engineering internship at our startup.

Are you available tomorrow?

Best,
Alex
""",

    "coffee": """
Hi Judy,

I saw your profile and would love to grab coffee
sometime next week to discuss a potential
collaboration opportunity.

Let me know when you're free!

Best,
Michael
""",

    "urgent": """
Hi Judy,

Could you finish this 40-page report by tonight?
I know it's Sunday, but it should only take
10 minutes.

Thanks,
Your Manager
""",

    "simple": """
Hi Judy,

Could you please send me the Zoom meeting link
for tomorrow's discussion?

Thanks,
Sarah
"""
}

# ==========================================
# Select Test Configuration
# ==========================================

# Change these values to control testing.
TEST_EMAIL = "interview"

# Options:
# "satirical" -> Test three Corporate Menace personas
# "normal"    -> Test three professional modes
# "all"       -> Test all six modes
TEST_GROUP = "satirical"

SATIRICAL_MODES = [
    "reverse_recruiter",
    "unicorn_gatekeeper",
    "infinite_bureaucrat"
]

NORMAL_MODES = [
    "professional",
    "negotiate",
    "accept"
]

if TEST_GROUP == "satirical":
    modes = SATIRICAL_MODES
elif TEST_GROUP == "normal":
    modes = NORMAL_MODES
elif TEST_GROUP == "all":
    modes = SATIRICAL_MODES + NORMAL_MODES
else:
    raise ValueError(
        f"Unknown test group: {TEST_GROUP}"
    )

if TEST_EMAIL not in test_emails:
    raise ValueError(
        f"Unknown test email: {TEST_EMAIL}"
    )

# ==========================================
# Run Tests
# ==========================================

print("=" * 60)
print("FOUNDERS-ONLY.IO — PERSONA TEST")
print("=" * 60)
print(f"Email scenario: {TEST_EMAIL}")
print(f"Test group: {TEST_GROUP}")
print(f"Number of API calls: {len(modes)}")

print("\nINCOMING EMAIL:")
print(test_emails[TEST_EMAIL].strip())

results = {}

for mode in modes:
    print(f"\n{'=' * 60}")
    print(f"MODE: {mode.upper()}")
    print("=" * 60)

    start_time = time.perf_counter()

    try:
        reply = generate_reply(
            email=test_emails[TEST_EMAIL],
            identity=identity,
            mode=mode
        )

        elapsed = time.perf_counter() - start_time

        results[mode] = {
            "reply": reply,
            "time": elapsed,
            "word_count": len(reply.split())
        }

        print(reply)
        print("\n--- METRICS ---")
        print(f"Response time: {elapsed:.2f}s")
        print(f"Word count: {len(reply.split())}")

        if len(reply.split()) > 120:
            print("WARNING: Reply exceeds 120 words!")

    except Exception as error:
        results[mode] = {
            "error": str(error)
        }
        print(f"ERROR: {error}")

# ==========================================
# Summary
# ==========================================

print(f"\n{'=' * 60}")
print("TEST SUMMARY")
print("=" * 60)

for mode, result in results.items():
    if "error" in result:
        print(f"[FAILED] {mode}: {result['error']}")
    else:
        print(
            f"[OK] {mode}: "
            f"{result['time']:.2f}s, "
            f"{result['word_count']} words"
        )
