"""Configuration manager for the Day Tracker application.

Manages the single-row Config table with JSON data.
"""
from app.models import db, Config


def get_config() -> dict:
    """Retrieve the current configuration, creating defaults if needed."""
    cfg = db.session.get(Config, 1)
    if cfg is None:
        cfg = Config(id=1, data=Config.default_data())
        db.session.add(cfg)
        db.session.commit()
    return cfg.data


def update_config(new_data: dict) -> dict:
    """Update the configuration with new data.

    Merges new_data into existing config (top-level keys replaced).
    """
    cfg = db.session.get(Config, 1)
    if cfg is None:
        cfg = Config(id=1, data=Config.default_data())
        db.session.add(cfg)

    merged = dict(cfg.data)  # copy existing
    merged.update(new_data)
    cfg.data = merged
    # SQLAlchemy needs to detect JSON mutation
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(cfg, "data")
    db.session.commit()
    return cfg.data


def reset_config() -> dict:
    """Reset configuration to defaults."""
    cfg = db.session.get(Config, 1)
    if cfg is None:
        cfg = Config(id=1, data=Config.default_data())
        db.session.add(cfg)
    else:
        cfg.data = Config.default_data()
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(cfg, "data")
    db.session.commit()
    return cfg.data
