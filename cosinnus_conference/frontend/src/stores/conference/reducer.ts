import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface Room {
  name: string
  type: string
  count: number
  url: string
}

export interface ConferenceState {
  name: string
  description: string
  rooms: {
    [r: string]: Room
  }
}

export function ConferenceReducer(
  state: ConferenceState = null,
  action: AnyAction
): ConferenceState {
  switch (action.type) {
    case ActionType.FETCH_CONFERENCE_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_CONFERENCE_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
