from backend import database

database.initialize_database()

database.save_review(
    "sample_bid.pdf",
    "GST, PAN, Turnover",
    "2 requirements matched; 1 needs manual review"
)

reviews = database.get_all_reviews()

for review in reviews:
    print(review)