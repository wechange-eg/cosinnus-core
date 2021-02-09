import moment from "moment"

import {Participant, ParticipantJson} from "../participants/models"

export interface Room {
  id: number
  slug: string
  title: string
  type: string
}

export interface EventJson {
  id: number
  title: string
  from_date: string
  to_date: string
  note_html: string
  is_break: boolean
  image_url?: string
  room: Room
  url: string
  is_queue_url: boolean
  raw_html: string
  presenters: ParticipantJson[]
  participants_limit: number
  feed_url: string
  management_urls?: {
    create_event: string
    update_event: string
    delete_event: string
  }
}

export interface EventProps {
  id: number
  title: string
  fromDate: Date
  toDate: Date
  noteHtml: string
  isBreak: boolean
  imageUrl?: string
  room: Room
  url: string
  isQueueUrl: boolean
  rawHtml: string
  presenters: Participant[]
  participantsLimit: number
  feedUrl: string
  managementUrls?: {
    createEvent: string
    updateEvent: string
    deleteEvent: string
  }
}

export class Event {
  props: EventProps

  public constructor(props: EventProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {Event} - Event object
   */
  public static fromJson(json: EventJson) : Event {
    const presenters: Participant[] = []
    json.presenters && json.presenters.forEach(json => presenters.push(Participant.fromJson(json)))
    const props: EventProps = {
      id: json.id,
      title: json.title,
      fromDate: new Date(json.from_date),
      toDate: new Date(json.to_date),
      noteHtml: json.note_html,
      isBreak: json.is_break,
      imageUrl: json.image_url,
      room: json.room,
      url: json.url,
      isQueueUrl: json.is_queue_url,
      rawHtml: json.raw_html,
      presenters: presenters,
      participantsLimit: json.participants_limit,
      feedUrl: json.feed_url,
      managementUrls: {
        createEvent: json.management_urls.create_event,
        updateEvent: json.management_urls.update_event,
        deleteEvent: json.management_urls.delete_event,
      },
    }

    return new Event(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {EventJson} - object in JSON format
   */
  toJson() : EventJson {
    const props = this.props
    const presenters: ParticipantJson[] = []
    props.presenters && props.presenters.forEach(p => presenters.push(p.toJson()))
    return {
      id: props.id,
      title: props.title,
      from_date: props.fromDate.toUTCString(),
      to_date: props.toDate.toUTCString(),
      note_html: props.noteHtml,
      is_break: props.isBreak,
      image_url: props.imageUrl,
      room: props.room,
      url: props.url,
      is_queue_url: props.isQueueUrl,
      raw_html: props.rawHtml,
      presenters: presenters,
      participants_limit: props.participantsLimit,
      feed_url: props.feedUrl,
      management_urls: {
        create_event: props.managementUrls.createEvent,
        update_event: props.managementUrls.updateEvent,
        delete_event: props.managementUrls.deleteEvent,
      },
    }
  }

  /**
   * Check if slot happens now
   *
   * @returns {boolean} true if slot happens now
   */
  isNow() : boolean {
    const now = new Date()
    const tenMinutesAgo = new Date(now.getTime() - (1000 * 60 * 10))
    return this.props.fromDate <= now && this.props.toDate >= tenMinutesAgo
  }

  /**
   * Get minutes left until end of event
   *
   * @returns {number} minutes
   */
  getMinutesLeft() : number {
    return parseInt((this.props.toDate.getTime() - new Date().getTime()) / 1000 / 60)
  }

  /**
   * Get internal url
   */
  getUrl() : string {
    if (this.props.isBreak) return ""
    // Lobby has no event routes
    if (this.props.room.type == "lobby") return ""
    return "../" + this.props.room.slug + "#/" + this.props.id
  }

  /**
   * Get note or comma separated list of presenters
   *
   * @returns {boolean} true if slot happens now
   */
  getNoteOrPresenters() : string {
    if (this.props.noteHtml) {
      return this.props.noteHtml
    } else if (this.props.presenters && this.props.presenters.length > 0) {
      return this.props.presenters.map(p => p.getFullName()).join(", ")
    }
    return ""
  }

  /**
   * Get available places left
   *
   * @returns {number} Number of places left, null if no limit
   */
  getAvailablePlaces(participantsCount: number) : number {
    if (this.props.participantsLimit) {
      const availablePlaces = this.props.participantsLimit - participantsCount
      return availablePlaces > 0 && availablePlaces || 0
    }
    return null
  }
}

export interface EventSlotJson {
  title?: string
  from_date: string
  to_date: string
  is_break: boolean
  events: EventJson[]
}

export interface EventSlotProps {
  title?: string
  fromDate: Date
  toDate: Date
  isBreak: boolean
  events: Event[]
}

export class EventSlot {
  props: EventSlotProps

  public constructor(props: EventSlotProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {EventSlot} - EventSlot object
   */
  public static fromJson(json: EventSlotJson) : EventSlot {
    const props: EventSlotProps = {
      title: json.title,
      fromDate: new Date(json.from_date),
      toDate: new Date(json.to_date),
      isBreak: json.is_break,
      events: []
    }
    if (json.events != null) {
      json.events.forEach((event: EventJson) => {
        props.events.push(Event.fromJson(event))
      })
    }
    return new EventSlot(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {EventSlotJson} - object in JSON format
   */
  toJson() : EventSlotJson {
    const props = this.props
    const events: EventJson[] = []
    if (props.events != null) {
      props.events.forEach((event: any) => {
        events.push(event.toJson())
      })
    }
    return {
      title: props.title,
      from_date: props.fromDate.toUTCString(),
      to_date: props.toDate.toUTCString(),
      is_break: props.isBreak,
      events: events,
    }
  }

  /**
   * Check if slot happens now
   *
   * @returns {boolean} true if slot happens now
   */
  isNow() : boolean {
    const now = new Date()
    const tenMinutesAgo = new Date(now.getTime() - (1000 * 60 * 10))
    return this.props.fromDate <= now && this.props.toDate >= tenMinutesAgo
  }
}

export interface EventDayJson {
  date: string
  slots: EventSlotJson[]
}

export interface EventDayProps {
  date: string
  slots: EventSlot[]
}

export class EventDay {
  props: EventDayProps

  public constructor(props: EventDayProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {EventDay} - EventDay object
   */
  public static fromJson(json: EventDayJson) : EventDay {
    const props: EventDayProps = {
      date: json.date,
      slots: []
    }
    if (json.slots != null) {
      json.slots.forEach((slot: EventSlotJson) => {
        props.slots.push(EventSlot.fromJson(slot))
      })
    }
    return new EventDay(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {EventDayJson} - object in JSON format
   */
  toJson() : EventDayJson {
    const props = this.props
    const slots: EventSlotJson[] = []
    if (props.slots != null) {
      props.slots.forEach((slot: EventSlot) => {
        slots.push(slot.toJson())
      })
    }
    return {
      date: props.date,
      slots: slots,
    }
  }

  /**
   * Check if date is today
   *
   * @returns {boolean} true if today
   */
  isToday() : boolean {
    return this.props.date == moment().format("YYYY-MM-DD")
  }

  /**
   * Check if date is tomorrow
   *
   * @returns {boolean} true if tomorrow
   */
  isTomorrow() : boolean {
    return this.props.date == moment().add(1, 'days').format("YYYY-MM-DD")
  }

  /**
   * Return current event slots
   *
   * @returns {EventSlot[]} current slots
   */
  getCurrentSlots() : EventSlot[] {
    return this.props.slots.filter(s => s.isNow())
  }

  /**
   * Return upcoming event slots
   *
   * @returns {EventSlot[]} upcoming slots
   */
  getUpcomingSlots() : EventSlot[] {
    return this.props.slots.filter(s => !s.isNow())
  }
}