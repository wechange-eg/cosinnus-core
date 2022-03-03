import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Organization} from "./models"

export function OrganizationsReducer(
  state: Organization[] = null,
  action: AnyAction
): Organization[] {
  switch (action.type) {
    case ActionType.FETCH_ORGANIZATIONS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_ORGANIZATIONS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
