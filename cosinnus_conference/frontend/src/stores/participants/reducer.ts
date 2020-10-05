import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Participant} from "./models"


export function ParticipantsReducer(
  state: Participant[] = [],
  action: AnyAction
): Participant[] {
  switch (action.type) {
    case ActionType.FETCH_PARTICIPANTS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_PARTICIPANTS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
