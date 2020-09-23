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
  note: string
  is_break: boolean
  image_url?: string
  room: Room
  url: string
  presenters: ParticipantJson[]
  participants_limit: number
  participants_count: number
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
  note: string
  isBreak: boolean
  imageUrl?: string
  room: Room
  url: string
  presenters: Participant[]
  participantsLimit: number
  participantsCount: number
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
   * @returns {User} - Event object
   */
  public static fromJson(json: EventJson) : Event {
    const presenters: Participant[] = []
    json.presenters && json.presenters.forEach(json => presenters.push(Participant.fromJson(json)))
    const props: EventProps = {
      id: json.id,
      title: json.title,
      fromDate: new Date(json.from_date),
      toDate: new Date(json.to_date),
      note: json.note,
      isBreak: json.is_break,
      imageUrl: json.image_url,
      room: json.room,
      url: json.url,
      presenters: presenters,
      participantsLimit: json.participants_limit,
      participantsCount: json.participants_count,
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
      note: props.note,
      is_break: props.isBreak,
      image_url: props.imageUrl,
      room: props.room,
      url: props.url,
      presenters: presenters,
      participants_limit: props.participantsLimit,
      participants_count: props.participantsCount,
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
    return this.props.fromDate <= now && this.props.toDate >= now
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
    if (this.props.note) {
      return this.props.note
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
  getAvailablePlaces() : number {
    if (this.props.participantsLimit) {
      return this.props.participantsLimit - this.props.participantsCount
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
   * @returns {User} - EventSlot object
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
      json.events.forEach((event: any) => {
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
    const events = []
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
    return this.props.fromDate <= now && this.props.toDate >= now
  }
}