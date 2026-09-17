import json


with open("baseline.json", "r") as file:
    BASELINE = json.load(file)


def get_status(value, baseline):

    if value <= baseline * 1.2:
        return "NORMAL"

    elif value <= baseline * 1.5:
        return "WARNING"

    else:
        return "HIGH"


def analyze_gases(mq2, mq4, mq7):

    mq2_status = get_status(mq2, BASELINE["mq2"])
    mq4_status = get_status(mq4, BASELINE["mq4"])
    mq7_status = get_status(mq7, BASELINE["mq7"])

    return {
        "mq2": {
            "value": mq2,
            "status": mq2_status
        },

        "mq4": {
            "value": mq4,
            "status": mq4_status
        },

        "mq7": {
            "value": mq7,
            "status": mq7_status
        }
    }