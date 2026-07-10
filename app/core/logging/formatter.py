import logging


class DetailedFormatter(logging.Formatter):
    def format(self, record):
        fields = []

        if hasattr(record, "source"):
            fields.append(f"source={record.source}")

        if hasattr(record, "user_id") and record.user_id is not None:
            fields.append(f"user_id={record.user_id}")

        if hasattr(record, "tg_user_id") and record.tg_user_id is not None:
            fields.append(f"tg_user_id={record.tg_user_id}")

        record.extra_fields = " | ".join(fields)

        return super().format(record)
