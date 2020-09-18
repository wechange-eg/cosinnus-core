export interface ParticipantJson {
  first_name: string
  last_name: string
  organisation: string
  location: string
}

export interface ParticipantProps {
  firstName: string
  lastName: string
  organisation: string
  location: string
}

export class Participant {
  props: ParticipantProps

  public constructor(props: ParticipantProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Participant object
   */
  public static fromJson(json: ParticipantJson) : Participant {
    const props: ParticipantProps = {
      firstName: json.first_name,
      lastName: json.last_name,
      organisation: json.organisation,
      location: json.location,
    }

    return new Participant(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {ParticipantJson} - object in JSON format
   */
  toJson() : ParticipantJson {
    const props = this.props
    return {
      first_name: props.firstName,
      last_name: props.lastName,
      organisation: props.organisation,
      location: props.location,
    }
  }
}

export interface Room {
  id: number
  slug: string
  title: string
}

export interface EventJson {
  id: number
  title: string
  from_date: string
  to_date: string
  note: string
  image_url?: string
  room: Room
  url: string
  participants_count?: number
  participants?: ParticipantJson[]
}


export interface EventProps {
  id: number
  title: string
  fromDate: Date
  toDate: Date
  note: string
  imageUrl?: string
  room: Room
  url: string
  participantsCount?: number
  participants?: Participant[]
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
    const participants: Participant[] = []
    json.participants && json.participants.forEach((json) => {
      participants.push(Participant.fromJson(json))
    })
    const props: EventProps = {
      id: json.id,
      title: json.title,
      fromDate: new Date(json.from_date),
      toDate: new Date(json.to_date),
      note: json.note,
      imageUrl: json.image_url,
      room: json.room,
      url: json.url,
      participantsCount: json.participants_count,
      participants: participants,
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
    const participants: ParticipantJson[] = []
    props.participants && props.participants.forEach((participant) => {
      participants.push(participant.toJson())
    })
    return {
      id: props.id,
      title: props.title,
      from_date: props.fromDate.toUTCString(),
      to_date: props.toDate.toUTCString(),
      note: props.note,
      image_url: props.imageUrl,
      room: props.room,
      url: props.url,
      participants_count: props.participantsCount,
      participants: participants,
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
    return (this.props.toDate.getTime() - new Date().getTime()) / 1000 / 60
  }
}

export interface EventSlotJson {
  title?: string
  from_date: string
  to_date: string
  events: EventJson[]
}

export interface EventSlotProps {
  title?: string
  fromDate: Date
  toDate: Date
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
