export interface ParticipantJson {
  id: number
  first_name: string
  last_name: string
  organization?: string
  country?: string
  chat_url?: string
  avatar_url?: string
  profile_url?: string
  location?: string
}

export interface ParticipantProps {
  id: number
  firstName: string
  lastName: string
  organization?: string
  country?: string
  chatUrl?: string
  avatarUrl?: string
  profileUrl?: string
  location?: string
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
      avatarUrl: json.avatar_url,
      profileUrl: json.profile_url,
      location: json.location
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
      avatar_url: props.avatarUrl,
      location: props.location
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

  getAvatarUrl() : string {
    if (!this.props.avatarUrl) return ""
    return this.props.avatarUrl
  }

  getProfileUrl() : string {
    if (!this.props.profileUrl) return ""
    return this.props.profileUrl
  }

  getLocation() : string {
    if (!this.props.location) return ""
    return this.props.location
  }

  /**
   * Get internal url
   */
  getUrl() : string {
    if (!this.props.chatUrl) return ""
    return "./#/" + this.props.id
  }
}
