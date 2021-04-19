export interface ParticipantJson {
  id: number
  first_name: string
  last_name: string
  organization?: string
  country?: string
  chat_url?: string
}

export interface ParticipantProps {
  id: number
  firstName: string
  lastName: string
  organization?: string
  country?: string
  chatUrl?: string
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
      id: json.id,
      firstName: json.first_name,
      lastName: json.last_name,
      organization: json.organization,
      country: json.country,
      chatUrl: json.chat_url,
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
      id: props.id,
      first_name: props.firstName,
      last_name: props.lastName,
      organization: props.organization,
      country: props.country,
      chat_url: props.chatUrl,
    }
  }

  /**
   * Get full name
   *
   * @returns {ParticipantJson} - object in JSON format
   */
  getFullName() : string {
    if (this.props.firstName && this.props.lastName) {
      return this.props.firstName + " " + this.props.lastName
    }
    return this.props.firstName || this.props.lastName || ""
  }

  /**
   * Get internal url
   */
  getUrl() : string {
    if (!this.props.chatUrl) return ""
    return "./#/" + this.props.id
  }
}
