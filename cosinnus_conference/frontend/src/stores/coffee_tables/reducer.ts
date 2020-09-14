import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Event} from "../events/models"

export function CoffeeTablesReducer(
  state: Event[] = null,
  action: AnyAction
): Event[] {
  switch (action.type) {
    case ActionType.FETCH_COFFEE_TABLES_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_COFFEE_TABLES_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
