import streamlit as st
import peewee as pw
from playhouse.migrate import SqliteMigrator, migrate

# 1. Database Connection
db = pw.SqliteDatabase("app_database.db")


# Enable foreign key support for SQLite
@db.connection_context()
def enable_foreign_keys():
    db.execute_sql("PRAGMA foreign_keys = ON;")


# 2. Define your models
class BaseModel(pw.Model):
    class Meta:
        database = db


# Example initial model
class User(BaseModel):
    username = pw.CharField(unique=True)
    email = pw.CharField(null=True)

    class Meta:
        table_name = "users"


# 3. Initialize database
def initialize_db():
    db.connect()
    enable_foreign_keys()
    db.create_tables(
        [User], safe=True
    )  # safe=True will not recreate tables if they exist
    st.success("Database initialized successfully!")


# 4. Migration functions for schema changes
def add_field_to_model():
    migrator = SqliteMigrator(db)

    # Check if the field already exists
    cursor = db.execute_sql("PRAGMA table_info(users);")
    columns = [column[1] for column in cursor.fetchall()]

    if "name" in columns:
        st.warning("Field 'name' already exists in the User model!")
        return

    # Example: Add a new field to the User model
    # First, add the field to your model definition above
    # Then, perform the migration:
    with db.atomic():
        migrate(
            # Add a 'name' field with default value 'Anonymous'
            migrator.add_column("users", "name", pw.CharField(default="Anonymous")),
        )
    st.success("Added 'name' field to User model!")


def rename_field():
    migrator = SqliteMigrator(db)

    # Check if source field exists and target field doesn't
    cursor = db.execute_sql("PRAGMA table_info(users);")
    columns = [column[1] for column in cursor.fetchall()]

    if "email" not in columns:
        st.warning("Source field 'email' doesn't exist in the User model!")
        return

    if "email_address" in columns:
        st.warning("Target field 'email_address' already exists in the User model!")
        return

    with db.atomic():
        migrate(
            # Rename 'email' field to 'email_address'
            migrator.rename_column("users", "email", "email_address"),
        )
    st.success("Renamed 'email' field to 'email_address'!")


def drop_field():
    migrator = SqliteMigrator(db)

    # Check if the field exists before dropping
    cursor = db.execute_sql("PRAGMA table_info(users);")
    columns = [column[1] for column in cursor.fetchall()]

    if "username" not in columns:
        st.warning("Field 'username' doesn't exist in the User model!")
        return

    # Check if this is the only field in the table (can't have empty tables)
    if len(columns) <= 1:
        st.error(
            "Cannot drop the only field in the table! Consider dropping the entire table instead."
        )
        return

    # Add confirmation to prevent accidental deletion
    if st.session_state.get("confirm_drop", False):
        with db.atomic():
            migrate(
                # Drop the 'username' field (be careful with this!)
                migrator.drop_column("users", "username"),
            )
        st.success("Dropped 'username' field!")
        st.session_state["confirm_drop"] = False
    else:
        st.warning("⚠️ Dropping fields can cause data loss! Are you sure?")
        if st.button("Yes, I'm sure - drop the field"):
            st.session_state["confirm_drop"] = True
            st.experimental_rerun()


# 5. Adding a completely new model
class Product(BaseModel):
    name = pw.CharField()
    price = pw.DecimalField(decimal_places=2)
    description = pw.TextField(null=True)

    class Meta:
        table_name = "products"


def add_new_model():
    # Check if the table already exists
    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='products';"
    )
    if cursor.fetchone():
        st.warning("Table 'products' already exists!")
        return

    db.create_tables([Product], safe=True)
    st.success("Added new 'Product' model to database!")


# 6. Helper function to check table/field existence
def check_field_exists(table, field):
    """Check if a specific field exists in a table"""
    cursor = db.execute_sql(f"PRAGMA table_info({table});")
    columns = [column[1] for column in cursor.fetchall()]
    return field in columns


def check_table_exists(table):
    """Check if a table exists in the database"""
    cursor = db.execute_sql(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';"
    )
    return cursor.fetchone() is not None


# 7. Streamlit UI
def main():
    st.title("Database Management with Peewee ORM")

    # Initialize session state for confirmations if not already set
    if "confirm_drop" not in st.session_state:
        st.session_state["confirm_drop"] = False

    if st.button("Initialize Database"):
        initialize_db()

    st.subheader("Database Migrations")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Add 'name' field"):
            add_field_to_model()

    with col2:
        if st.button("Rename 'email' field"):
            rename_field()

    with col3:
        if st.button("Drop 'username' field"):
            drop_field()

    if st.button("Add 'Product' model"):
        add_new_model()

    # Add a section for more complex migrations
    st.subheader("Advanced Operations")

    # Example of adding a field with custom SQL validation
    with st.expander("Add Custom Field"):
        field_name = st.text_input("Field Name")
        field_type = st.selectbox(
            "Field Type",
            [
                "CharField",
                "IntegerField",
                "BooleanField",
                "TextField",
                "DateTimeField",
                "DecimalField",
            ],
        )
        default_value = st.text_input("Default Value (optional)")

        if st.button("Add Field") and field_name:
            try:
                # Check if field already exists
                if check_field_exists("users", field_name):
                    st.warning(f"Field '{field_name}' already exists!")
                else:
                    # Map field types to Peewee field classes
                    field_mapping = {
                        "CharField": pw.CharField(
                            default=default_value if default_value else ""
                        ),
                        "IntegerField": pw.IntegerField(
                            default=int(default_value) if default_value else 0
                        ),
                        "BooleanField": pw.BooleanField(
                            default=bool(default_value) if default_value else False
                        ),
                        "TextField": pw.TextField(
                            default=default_value if default_value else ""
                        ),
                        "DateTimeField": pw.DateTimeField(null=True),
                        "DecimalField": pw.DecimalField(
                            decimal_places=2,
                            default=float(default_value) if default_value else 0.0,
                        ),
                    }

                    migrator = SqliteMigrator(db)
                    with db.atomic():
                        migrate(
                            migrator.add_column(
                                "users", field_name, field_mapping[field_type]
                            ),
                        )
                    st.success(f"Added '{field_name}' field with type {field_type}!")
            except Exception as e:
                st.error(f"Error: {e}")

    # Display current database structure
    if st.button("Show Database Schema"):
        try:
            db.connect(reuse_if_open=True)
            cursor = db.execute_sql(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            tables = [row[0] for row in cursor.fetchall()]

            st.write("### Database Tables")
            for table in tables:
                if table != "sqlite_sequence":  # Skip internal SQLite tables
                    st.write(f"**Table: {table}**")
                    cursor = db.execute_sql(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()

                    # Create a more readable table format
                    col_data = []
                    for col in columns:
                        col_data.append(
                            {
                                "Name": col[1],
                                "Type": col[2],
                                "Nullable": "No" if col[3] == 0 else "Yes",
                                "PK": "✓" if col[5] == 1 else "",
                            }
                        )

                    st.table(col_data)

                    # Show row count
                    count = db.execute_sql(f"SELECT COUNT(*) FROM {table}").fetchone()[
                        0
                    ]
                    st.caption(f"Total rows: {count}")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if not db.is_closed():
                db.close()


if __name__ == "__main__":
    main()
