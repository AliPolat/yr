import streamlit as st
import peewee as pw
from playhouse.migrate import SqliteMigrator, migrate

# 1. Database Connection
db = pw.SqliteDatabase("app_database.db")


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
    db.create_tables(
        [User], safe=True
    )  # safe=True will not recreate tables if they exist
    st.success("Database initialized successfully!")


# 4. Migration functions for schema changes
def add_field_to_model():
    migrator = SqliteMigrator(db)

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

    with db.atomic():
        migrate(
            # Rename 'email' field to 'email_address'
            migrator.rename_column("users", "email", "email_address"),
        )
    st.success("Renamed 'email' field to 'email_address'!")


def drop_field():
    migrator = SqliteMigrator(db)

    with db.atomic():
        migrate(
            # Drop the 'username' field (be careful with this!)
            migrator.drop_column("users", "username"),
        )
    st.success("Dropped 'username' field!")


# 5. Adding a completely new model
class Product(BaseModel):
    name = pw.CharField()
    price = pw.DecimalField(decimal_places=2)
    description = pw.TextField(null=True)

    class Meta:
        table_name = "products"


def add_new_model():
    db.create_tables([Product], safe=True)
    st.success("Added new 'Product' model to database!")


# 6. Streamlit UI
def main():
    st.title("Database Management with Peewee ORM")

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
                    for col in columns:
                        st.write(f"- {col[1]} ({col[2]})")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if not db.is_closed():
                db.close()


if __name__ == "__main__":
    main()
