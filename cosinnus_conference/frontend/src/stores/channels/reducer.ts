import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface Channel {
  id: string
  name: string
}

export function ChannelsReducer(
  state: Channel[] = null,
  action: AnyAction
): Channel[] {
  switch (action.type) {
    case ActionType.FETCH_CHANNELS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_CHANNELS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
