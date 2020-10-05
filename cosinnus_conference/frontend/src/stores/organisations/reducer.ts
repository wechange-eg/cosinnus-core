import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Organisation} from "./models"

export function OrganisationsReducer(
  state: Organisation[] = null,
  action: AnyAction
): Organisation[] {
  switch (action.type) {
    case ActionType.FETCH_ORGANISATIONS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_ORGANISATIONS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
