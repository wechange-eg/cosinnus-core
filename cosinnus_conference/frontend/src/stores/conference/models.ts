import {Room, RoomJson} from "../room/models"

export interface ConferenceJson {
  id: number
  name: string
  description: string
  rooms: RoomJson[]
  management_urls: {
    manage_conference: string
    manage_rooms: string
    manage_events: string
    manage_memberships: string
  }
  header_notification: {
    notification_text: string
    link_text: string
    link_url: string
  }
  theme_color: string
  dates: string[]
  avatar: string
  wallpaper: string
  images: string[]
}

export interface ConferenceProps {
  id: number
  name: string
  description: string
  rooms: Room[]
  managementUrls: {
    manageConference: string
    manageRooms: string
    manageEvents: string
    manageMemberships: string
  }
  headerNotification: {
    notificationText: string
    linkText: string
    linkUrl: string
  }
  themeColor: string
  dates: string[]
  avatar: string
  wallpaper: string
  images: string[]
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
      id: json.id,
      name: json.name,
      description: json.description,
      rooms: [],
      managementUrls: {
        manageConference: json.management_urls.manage_conference,
        manageRooms: json.management_urls.manage_rooms,
        manageEvents: json.management_urls.manage_events,
        manageMemberships: json.management_urls.manage_memberships,
      },
      headerNotification: {
        notificationText: json.header_notification.notification_text,
        linkText: json.header_notification.link_text,
        linkUrl: json.header_notification.link_url,
      },
      themeColor: json.theme_color,
      dates: json.dates,
      avatar: json.avatar,
      wallpaper: json.wallpaper,
      images: json.images,
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
    const rooms: RoomJson[] = []
    if (props.rooms != null) {
      props.rooms.forEach((room: any) => {
        rooms.push(room.toJson())
      })
    }
    return {
      id: props.id,
      name: props.name,
      description: props.description,
      rooms: rooms,
      management_urls: {
        manage_conference: props.managementUrls.manageConference,
        manage_rooms: props.managementUrls.manageRooms,
        manage_events: props.managementUrls.manageEvents,
        manage_memberships: props.managementUrls.manageMemberships,
      },  
      header_notification: {
        notification_text: props.headerNotification.notificationText,
        link_text: props.headerNotification.linkText,
        link_url: props.headerNotification.linkUrl,
      },
      theme_color: props.themeColor,
      dates: props.dates,
      avatar: props.avatar,
      wallpaper: props.wallpaper,
      images: props.images,
    }
  }

  /**
   * Get theme color
   *
   * @returns {string} Color including # or undefined if none
   */
  getThemeColor() : string {
    return this.props.themeColor && '#' + this.props.themeColor || undefined
  }
}
