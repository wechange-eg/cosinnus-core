import {EventJson, Event, EventSlot} from "../stores/events/models"
import moment from "moment"

/**
 * Group events by event slots (using only their starting time)
 *
 * @returns EventSlot[]
 */
export const groupBySlots = (events: EventJson[]) => {
  const slots: {
    [s: string]: EventSlot
  } = {}
  events.map((event) => {
    if (!(event.from_date in slots)) {
      slots[event.from_date] = EventSlot.fromJson({
        title: event.title,
        from_date: event.from_date,
        to_date: event.to_date,
        is_break: event.is_break,
        events: []
      })
    }
    event.id && slots[event.from_date].props.events.push(Event.fromJson(event))
  })
  return Object.keys(slots).sort().map((k) => slots[k])
}

/**
 * Group events by event slots (using only their starting time)
 *
 * @returns EventSlot[]
 */
export const filterCurrentAndRoom = (slots: EventSlot[], room: string) => {
  let currentSlot: EventSlot = null
  slots && slots.map((slot) => {
    if (slot.isNow()) {
      currentSlot = slot
      const eventsInRoom = currentSlot.props.events.filter((slot) => slot.props.roomSlug === room)
      currentSlot.props.events = eventsInRoom
    }
  })
  return currentSlot
}

/**
 * Format time
 *
 * @returns string
 */
export const formatTime = (datetime: Date) => {
  return moment(datetime).format("HH:mm")
}

/**
 * Get event from event slots using ID
 *
 * @returns Event
 */
export const findEventById = (slots: EventSlot[], eventId: number): Event => {
  let event: Event = null
  for (let i = 0; i < slots.length; i++) {
    event = slots[i].props.events.find((e) => e.props.id === eventId)
    if (event) break
  }
  return event
}
