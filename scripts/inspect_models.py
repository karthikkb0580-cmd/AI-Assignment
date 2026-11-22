from sqlalchemy import inspect

from ai_pipeline.database.models import (
    Startup,
    Product,
    SourceRecord,
)


def inspect_model(model):
    mapper = inspect(model)

    print("\n" + "=" * 65)
    print(f"MODEL: {model.__name__}")
    print(f"TABLE: {model.__tablename__}")
    print("=" * 65)

    print("\nCOLUMNS:")

    for column in mapper.columns:
        print(
            f"Name: {column.name:<25} "
            f"Type: {str(column.type):<20} "
            f"Nullable: {column.nullable} "
            f"Primary Key: {column.primary_key}"
        )

    print("\nUNIQUE CONSTRAINTS:")

    for constraint in model.__table__.constraints:
        if getattr(constraint, "unique", False):
            print(constraint)

        if constraint.__class__.__name__ == "UniqueConstraint":
            print(
                [column.name for column in constraint.columns]
            )


def main():
    inspect_model(Startup)
    inspect_model(Product)
    inspect_model(SourceRecord)


if __name__ == "__main__":
    main()