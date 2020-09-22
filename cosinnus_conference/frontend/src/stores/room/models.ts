export interface RoomJson {
  id: number
  slug: string
  title: string
  type: string
  count: number
  url: string
  description: string
  management_urls: {
    create_event?: string
    update_room?: string
    delete_room?: string
  }
  is_visible: boolean
}

export interface RoomProps {
  id: number
  slug: string
  title: string
  type: string
  count: number
  url: string
  description: string
  managementUrls: {
    createEvent?: string
    updateRoom?: string
    deleteRoom?: string
  }
  isVisible: boolean
}

export class Room {
  props: RoomProps

  public constructor(props: RoomProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Room object
   */
  public static fromJson(json: RoomJson) : Room {
    const props: RoomProps = {
      id: json.id,
      slug: json.slug,
      title: json.title,
      type: json.type,
      count: json.count,
      url: json.url,
      description: json.description,
      managementUrls: {
        createEvent: json.management_urls.create_event,
        updateRoom: json.management_urls.update_room,
        deleteRoom: json.management_urls.delete_room,
      },
      isVisible: json.is_visible,
    }

    return new Room(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {RoomJson} - object in JSON format
   */
  toJson() : RoomJson {
    const props = this.props
    return {
      id: props.id,
      slug: props.slug,
      title: props.title,
      type: props.type,
      count: props.count,
      url: props.url,
      description: props.description,
      management_urls: {
        create_event: props.managementUrls.createEvent,
        update_room: props.managementUrls.updateRoom,
        delete_room: props.managementUrls.deleteRoom,
      },
      is_visible: props.isVisible,
    }
  }
}
