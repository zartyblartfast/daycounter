"""SQLAlchemy database models for the Day Tracker application."""
import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Config(db.Model):
    """Single-row config table storing JSON configuration."""
    __tablename__ = "config"

    id = db.Column(db.Integer, primary_key=True, default=1)
    data = db.Column(db.JSON, nullable=False)

    @staticmethod
    def default_data() -> dict:
        return {
            "departure_date": "2026-03-26",
            "first_full_nonresident_tax_year": "2026-2027",
            "profiles": {
                "year_1": {
                    "target_midnights": 30,
                    "stat_limit_midnights": 90,
                    "buffer": 5,
                },
                "year_2": {
                    "target_midnights": 85,
                    "stat_limit_midnights": 90,
                    "buffer": 5,
                },
                "year_3_plus": {
                    "target_midnights": 120,
                    "stat_limit_midnights": 120,
                    "buffer": 5,
                },
            },
            "backup_retention_count": 10,
        }


class Travel(db.Model):
    """A travel event / stay record."""
    __tablename__ = "travel"

    id = db.Column(db.Integer, primary_key=True)
    departure_date = db.Column(db.Date, nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    destination_country = db.Column(db.String(100), nullable=False)
    is_uk = db.Column(db.Boolean, nullable=False, default=False)
    return_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.datetime.utcnow()
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.datetime.utcnow(),
        onupdate=lambda: datetime.datetime.utcnow(),
    )

    evidence_files = db.relationship(
        "EvidenceFile", backref="travel", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Travel {self.id}: {self.destination_country} "
            f"{self.arrival_date} - {self.return_date}>"
        )


class EvidenceFile(db.Model):
    """Evidence file linked to a travel or general."""
    __tablename__ = "evidence_file"

    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(
        db.Integer, db.ForeignKey("travel.id"), nullable=True
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)  # SHA-256
    category = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # comma-separated
    uploaded_at = db.Column(
        db.DateTime, default=lambda: datetime.datetime.utcnow()
    )
    tax_year = db.Column(db.String(9), nullable=True)  # e.g. '2026-2027'

    def __repr__(self):
        return f"<EvidenceFile {self.id}: {self.original_filename}>"


class AnnualStatement(db.Model):
    """Generated annual residency statement."""
    __tablename__ = "annual_statement"

    id = db.Column(db.Integer, primary_key=True)
    tax_year = db.Column(db.String(9), nullable=False)
    generated_at = db.Column(
        db.DateTime, default=lambda: datetime.datetime.utcnow()
    )
    filename = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)

    def __repr__(self):
        return f"<AnnualStatement {self.id}: {self.tax_year}>"


# Evidence categories
EVIDENCE_CATEGORIES = [
    ("ferry_booking", "Ferry Booking"),
    ("flight_booking", "Flight Booking"),
    ("hotel_receipt", "Hotel Receipt"),
    ("landlord_email", "Landlord Email/Letter"),
    ("bank_statement", "Bank Statement"),
    ("gp_registration", "GP Registration"),
    ("car_registration", "Car Registration"),
    ("utility_bill", "Utility Bill"),
    ("passport_stamp", "Passport Stamp"),
    ("boarding_pass", "Boarding Pass"),
    ("other", "Other"),
]
