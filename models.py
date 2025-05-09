import peewee as pw
from datetime import date

# Create a database
db = pw.SqliteDatabase("yatmaz_robot.db")


# Base Model
class BaseModel(pw.Model):
    class Meta:
        database = db


# User Model
class User(BaseModel):
    user_id = pw.AutoField(
        primary_key=True
    )  # Using AutoField for auto-incrementing primary key
    nick_name = pw.CharField(max_length=100)
    real_name = pw.CharField(max_length=100)
    comment = pw.CharField(max_length=500, null=True)

    def __str__(self):
        return f"{self.nick_name} ({self.real_name})"


# Stock/Asset Model
class StockAsset(BaseModel):
    stock_asset_id = pw.AutoField(
        primary_key=True
    )  # Using AutoField for auto-incrementing primary key
    user = pw.ForeignKeyField(User, backref="assets")
    stock_asset_code = pw.CharField(max_length=20)
    stock_asset_name = pw.CharField(max_length=100)
    buy_date = pw.DateField(default=date.today)
    buy_price = pw.DecimalField(decimal_places=2, auto_round=True, max_digits=10)
    sell_date = pw.DateField(null=True)
    sell_price = pw.DecimalField(
        decimal_places=2, auto_round=True, max_digits=10, null=True
    )
    status = pw.CharField(
        max_length=20, default="Position"
    )  # Either 'Position' or 'Cash'

    def __str__(self):
        return f"{self.stock_asset_code} - {self.status}"


# Create tables if they don't exist
def create_tables():
    with db:
        db.create_tables([User, StockAsset], safe=True)
