import {Room, RoomJson} from "../room/models"

export interface ConferenceJson {
  name: string
  description: string
  rooms: RoomJson[]
  management_url: string
}

export interface ConferenceProps {
  name: string
  description: string
  rooms: Room[]
  managementUrl: string
}

export class Conference {
  props: ConferenceProps

  public constructor(props: ConferenceProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Conference object
   */
  public static fromJson(json: ConferenceJson) : Conference {
    const props: ConferenceProps = {
      name: json.name,
      description: json.description,
      rooms: [],
      managementUrl: json.management_url,
    }
    if (json.rooms != null) {
      json.rooms.forEach((room: any) => {
        props.rooms.push(Room.fromJson(room))
      })
    }

    return new Conference(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {ConferenceJson} - object in JSON format
   */
  toJson() : ConferenceJson {
    const props = this.props
    const rooms = []
    if (props.rooms != null) {
      props.rooms.forEach((room: any) => {
        rooms.push(room.toJson())
      })
    }
    return {
      name: props.name,
      description: props.description,
      rooms: rooms,
      management_url: props.managementUrl,
    }
  }
}
