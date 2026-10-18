"""The `estate` sample database: an application's own tables, kept apart from DMC's schema.

Harvest (Phase 1) reads these through a read-only role; the Phase 2 `retention_window` rule runs
against their ages. Rows are placed relative to the moment of loading, so some are always older
than the sample retention policies (`r1y` 365 days, `r7y` 2555 days) and the rule can fail on
them whenever it is run. Loading creates what is missing and fills only empty tables, so it is
safe to run again.
"""

from dataclasses import dataclass

from sqlalchemy import Connection, text

# (full_name, email, phone, date_of_birth, days since last login, days since created)
_CUSTOMERS: tuple[tuple[str, str, str, str, int, int], ...] = (
    ("Amelia Hartley", "amelia.hartley@example.com", "+44 20 7946 0101", "1988-03-14", 3, 900),
    ("Jonas Weber", "jonas.weber@example.com", "+49 30 901820", "1979-11-02", 21, 1500),
    ("Priyanka Nair", "priyanka.nair@example.com", "+91 22 5550 0142", "1992-07-30", 400, 1100),
    ("Carlos Mendes", "carlos.mendes@example.com", "+351 21 555 0178", "1985-01-22", 760, 2100),
    ("Sara Lindqvist", "sara.lindqvist@example.com", "+46 8 555 0133", "1996-09-09", 1200, 2900),
    ("Tom Okonkwo", "tom.okonkwo@example.com", "+44 161 555 0166", "1974-05-18", 2800, 3300),
    ("Mei Tanaka", "mei.tanaka@example.com", "+81 3 5550 0190", "2001-12-01", 5, 120),
    ("Lucas Moreau", "lucas.moreau@example.com", "+33 1 5550 0112", "1969-04-27", 3100, 3900),
)

# (customer index, total, card last four, shipping address, days since placed)
_ORDERS: tuple[tuple[int, str, str, str, int], ...] = (
    (0, "42.50", "4242", "14 Marsh Lane, London E1 6QL", 12),
    (0, "118.00", "4242", "14 Marsh Lane, London E1 6QL", 640),
    (1, "9.99", "0005", "Kastanienallee 7, 10435 Berlin", 30),
    (2, "230.40", "1881", "22 Residency Rd, Pune 411001", 410),
    (3, "76.25", "9424", "Rua das Flores 18, 1200-195 Lisboa", 780),
    (4, "15.00", "3155", "Storgatan 4, 114 55 Stockholm", 1300),
    (5, "310.00", "7777", "9 Canal St, Manchester M1 3EZ", 2700),
    (5, "64.80", "7777", "9 Canal St, Manchester M1 3EZ", 2950),
    (6, "27.90", "0119", "2-4-1 Shibuya, Tokyo 150-0002", 4),
    (7, "55.00", "6011", "8 Rue de Rivoli, 75004 Paris", 3050),
)

# (customer index, subject, body, days since opened)
_TICKETS: tuple[tuple[int, str, str, int], ...] = (
    (0, "Where is my parcel?", "Order not delivered yet; please check the courier.", 9),
    (1, "Change of address", "I moved. New address is Kastanienallee 7, Berlin.", 45),
    (2, "Refund request", "Item arrived damaged. Photo attached to my earlier email.", 395),
    (3, "Cannot log in", "Password reset email never arrives at carlos.mendes@example.com.", 700),
    (4, "Delete my account", "Please remove all my data, I no longer use the shop.", 1150),
    (5, "Wrong invoice", "VAT number on the invoice is wrong.", 2600),
    (7, "Newsletter unsubscribe", "Still receiving mail after unsubscribing twice.", 2990),
)

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS customers (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        full_name text NOT NULL,
        email text NOT NULL UNIQUE,
        phone text,
        date_of_birth date,
        created_at timestamptz NOT NULL,
        last_login_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        customer_id bigint NOT NULL REFERENCES customers (id),
        total numeric(10, 2) NOT NULL,
        card_last4 char(4),
        shipping_address text,
        placed_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS support_tickets (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        customer_id bigint NOT NULL REFERENCES customers (id),
        subject text NOT NULL,
        body text,
        opened_at timestamptz NOT NULL
    )
    """,
)

TABLES = ("customers", "orders", "support_tickets")


@dataclass(frozen=True)
class EstateLoad:
    tables_created: int
    rows_inserted: int


def _days_ago(days: int) -> str:
    return f"now() - make_interval(days => {int(days)})"


def load_estate(connection: Connection) -> EstateLoad:
    """Create the sample tables and fill the empty ones. The caller commits."""
    existing = set(
        connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).scalars()
    )
    for statement in _DDL:
        connection.execute(text(statement))
    inserted = 0
    if _is_empty(connection, "customers"):
        for name, email, phone, dob, login_days, created_days in _CUSTOMERS:
            connection.execute(
                text(
                    "INSERT INTO customers (full_name, email, phone, date_of_birth, created_at,"
                    f" last_login_at) VALUES (:n, :e, :p, :d, {_days_ago(created_days)},"
                    f" {_days_ago(login_days)})"
                ),
                {"n": name, "e": email, "p": phone, "d": dob},
            )
        inserted += len(_CUSTOMERS)
    ids = connection.execute(text("SELECT id FROM customers ORDER BY id")).scalars().all()
    if _is_empty(connection, "orders"):
        for index, total, card, address, days in _ORDERS:
            connection.execute(
                text(
                    "INSERT INTO orders (customer_id, total, card_last4, shipping_address,"
                    f" placed_at) VALUES (:c, :t, :k, :a, {_days_ago(days)})"
                ),
                {"c": ids[index], "t": total, "k": card, "a": address},
            )
        inserted += len(_ORDERS)
    if _is_empty(connection, "support_tickets"):
        for index, subject, body, days in _TICKETS:
            connection.execute(
                text(
                    "INSERT INTO support_tickets (customer_id, subject, body, opened_at)"
                    f" VALUES (:c, :s, :b, {_days_ago(days)})"
                ),
                {"c": ids[index], "s": subject, "b": body},
            )
        inserted += len(_TICKETS)
    return EstateLoad(
        tables_created=len(set(TABLES) - existing),
        rows_inserted=inserted,
    )


def _is_empty(connection: Connection, table: str) -> bool:
    return bool(connection.execute(text(f"SELECT NOT EXISTS (SELECT 1 FROM {table})")).scalar_one())
