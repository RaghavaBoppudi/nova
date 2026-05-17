import EventKit
import time


def request_calendar_access():
    store = EventKit.EKEventStore.alloc().init()

    access_granted = []

    def completion_handler(granted, error):
        access_granted.append(granted)

    store.requestFullAccessToEventsWithCompletion_(completion_handler)

    # Wait for the permission dialog
    timeout = 10
    while not access_granted and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5

    if access_granted and access_granted[0]:
        print("Calendar access granted.")
    else:
        print("Calendar access denied or timed out.")

    return store if access_granted and access_granted[0] else None


if __name__ == "__main__":
    store = request_calendar_access()
    if store:
        calendars = store.calendarsForEntityType_(0)
        print(f"Found {len(calendars)} calendars:")
        for cal in calendars:
            print(f"  - {cal.title()}")
