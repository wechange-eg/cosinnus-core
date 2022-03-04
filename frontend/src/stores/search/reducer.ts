import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Result} from "./models"

export interface SearchState {
  term: string
  results: Result[]
  error?: string
}

export function SearchReducer(
  state: SearchState = { term: "", results: null},
  action: AnyAction
): SearchState {
  switch (action.type) {
    case ActionType.FETCH_SEARCH_RESULTS_SUCCESS: {
      return {
        ...state,
        results: action.payload,
        error: null
      }
    }
    case ActionType.FETCH_SEARCH_RESULTS_ERROR: {
      return {
        ...state,
        results: null,
        error: action.payload
      }
    }
    default: {
      return state
    }
  }
}
