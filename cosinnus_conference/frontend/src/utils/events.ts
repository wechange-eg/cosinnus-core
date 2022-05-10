import moment from "moment"
import "moment-timezone"

import {Event, EventDay, EventDayProps, EventSlot, EventSlotProps} from "../stores/events/models"

/**
 * Group events by days and slots (using only their starting time)
 *
 * @returns EventDay[]
 */
export const groupByDaysAndSlots = (events: Event[]) => {
  // Group days and slots
  const days: {
    [s: string]: {
      [s: string]: Event[]
    }
  } = {}
  events.map((event) => {
    let dayKey = moment(event.props.fromDate).format("YYYY-MM-DD")
    let slotKey = event.props.fromDate.toUTCString()
    if (window.hasOwnProperty('cosinnus_user_timezone') && window.cosinnus_user_timezone) {
      const userDate = moment(event.props.fromDate).tz(window.cosinnus_user_timezone)
      dayKey = userDate.format('YYYY-MM-DD')
      slotKey = userDate.format()
    }
    if (!(dayKey in days)) days[dayKey] = {}
    if (!(slotKey in days[dayKey])) days[dayKey][slotKey] = []
    days[dayKey][slotKey].push(event)
  })
  // Create EventDay and EventSlot objects
  return Object.keys(days).sort().map((dayKey) => {
    const day = days[dayKey]
    const slots: EventSlot[] = Object.keys(day).sort().map((slotKey) => {
      const events = day[slotKey]
      return new EventSlot({
        title: events[0].props.title,
        fromDate: events[0].props.fromDate,
        toDate: events[0].props.toDate,
        isBreak: events[0].props.isBreak,
        events: events.sort((a, b) => (a.props.title > b.props.title) ? 1 : -1)
      })
    })
    return new EventDay({
      date: dayKey,
      slots: slots
    })
  })
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
  if (window.hasOwnProperty('cosinnus_user_timezone') && window.cosinnus_user_timezone) {
    return moment(datetime).tz(window.cosinnus_user_timezone).format('HH:mm')
  }
  return moment(datetime).format('HH:mm')
}

/**
 * Get timezone from date
 *
 * @returns string
 */
export const getTimezoneForUser = (): string => {
  if (window.hasOwnProperty('cosinnus_user_timezone') && window.cosinnus_user_timezone) {
    return `(${window.cosinnus_user_timezone})`
  }
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  return `(${timezone})`
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

/**
 * Get current day for tab navigation (current, next or first in this order)
 *
 * @returns string
 */
export const getCurrentDay = (days: EventDay[]): string => {
  const today = moment().format("YYYY-MM-DD")
  const day = days.find((d) => d.props.date >= today)
  if (day) {
    return day.props.date
  } else {
    return days[0].props.date
  }
}
