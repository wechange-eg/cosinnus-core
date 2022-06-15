import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import axios from 'axios'

// todo: props in the reducer/slice?
export interface SettingsJson {
  name: string
  background_image: string
  logo_image: string
  top_color: string
  bottom_color: string
  extra_css: string
}

export interface SettingsProps {
  name: string
  backgroundImage: string
  logoImage: string
  topColor: string
  bottomColor: string
  extraCss: string
}

export interface SettingsState {
  settings: SettingsProps
}

export class Settings {
  props: SettingsProps

  public constructor(props: SettingsProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Settings object
   */
  public static fromJson(json: SettingsJson): Settings {
    const props: SettingsProps = {
      name: json.name,
      backgroundImage: json.background_image,
      logoImage: json.logo_image,
      topColor: json.top_color,
      bottomColor: json.bottom_color,
      extraCss: json.extra_css,
    }

    return new Settings(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {SettingsJson} - object in JSON format
   */
  toJson(): SettingsJson {
    const { props } = this
    return {
      name: props.name,
      background_image: props.backgroundImage,
      logo_image: props.logoImage,
      top_color: props.topColor,
      bottom_color: props.bottomColor,
      extra_css: props.extraCss,
    }
  }

  /**
   * Get theme color
   *
   * @returns {string} Color including # or undefined if none
   */
  getThemeColor(): string {
    return (this.props.topColor && `#${this.props.topColor}`) || undefined
  }

  /**
   * Get logo URL
   *
   * @returns {string} Absolute URL
   */
  getLogoUrl(): string {
    if (this.props.logoImage) {
      return `${process.env.BASE_URL}/${this.props.logoImage}`
    }
    return undefined
  }
}

const API_URL = `${process.env.API_URL}`

export const fetchSettings = createAsyncThunk(
  'settings/fetch',
  async (
    values: null,
  ): Promise<SettingsProps | undefined> => {
    const { data } = await axios.get<SettingsJson>(
      `${API_URL}/settings/`,
      values,
    )
    return Settings.fromJson(data).props
  },
)

const settingsSlice = createSlice({
  name: 'settings',
  initialState: {} as SettingsState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchSettings.fulfilled, (state, action) => {
        if (!action.payload) return
        // eslint-disable-next-line no-param-reassign
        state.settings = action.payload
      })
  },
})

export const { actions } = settingsSlice
export default settingsSlice.reducer
