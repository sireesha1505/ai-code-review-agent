EVALUATION_DATASET = [
    {
        "name": "sql_injection",
        "files": [
            {
                "filename": "users.py",
                "patch": """
+def get_user(db, username):
+    query = f"SELECT * FROM users WHERE name = '{username}'"
+    return db.execute(query).fetchone()
"""
            }
        ],
        "expected": {
            "required_categories": ["security"],
            "allowed_categories": ["security"]
        }
    },

    {
        "name": "nested_loop_performance",
        "files": [
            {
                "filename": "users.py",
                "patch": """
+def find_matches(users, orders):
+    result = []
+    for user in users:
+        for order in orders:
+            if user.id == order.user_id:
+                result.append(order)
+    return result
"""
            }
        ],
        "expected": {
            "required_categories": ["performance"],
            "allowed_categories": ["performance"]
        }
    },

    {
        "name": "off_by_one_bug",
        "files": [
            {
                "filename": "numbers.py",
                "patch": """
+def get_first_three(numbers):
+    return numbers[0:4]
"""
            }
        ],
        "expected": {
            "required_categories": ["bug"],
            "allowed_categories": ["bug"]
        }
    },

    {
        "name": "missing_tests",
        "files": [
            {
                "filename": "discount.py",
                "patch": """
+def calculate_discount(price, discount):
+    return price - (price * discount)
"""
            }
        ],
        "expected": {
            "required_categories": ["testing"],
            "allowed_categories": ["testing"]
        }
    },

    {
        "name": "missing_type_hints",
        "files": [
            {
                "filename": "users.py",
                "patch": """
+def get_users(db):
+    return db.query(User).all()
"""
            }
        ],
        "expected": {
            "required_categories": ["maintainability"],
            "allowed_categories": ["maintainability"]
        }
    }
]