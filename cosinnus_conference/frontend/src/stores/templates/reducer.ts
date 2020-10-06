import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {ChatTemplate} from "./effects"

export interface TemplatesState {
  user: ChatTemplate[]
  team: ChatTemplate[]
  pending: boolean | null
  errorMessage?: string | null
}

export function TemplatesReducer(
  state: TemplatesState = { user: [], team: [], pending: false },
  action: AnyAction
): TemplatesState {
  switch (action.type) {
    case ActionType.FETCH_USER_CHAT_TEMPLATES: {
      return {
        ...state,
        pending: true,
        user: []
      }
    }
    case ActionType.FETCH_USER_CHAT_TEMPLATES_SUCCESS: {
      return {
        ...state,
        pending: false,
        user: action.payload
      }
    }
    case ActionType.FETCH_USER_CHAT_TEMPLATES_ERROR: {
      return {
        ...state,
        user: [],
        errorMessage: action.payload.message
      }
    }
    case ActionType.FETCH_TEAM_CHAT_TEMPLATES: {
      return {
        ...state,
        pending: true,
        team: []
      }
    }
    case ActionType.FETCH_TEAM_CHAT_TEMPLATES_SUCCESS: {
      return {
        ...state,
        pending: false,
        team: action.payload
      }
    }
    case ActionType.FETCH_TEAM_CHAT_TEMPLATES_ERROR: {
      return {
        ...state,
        team: [],
        errorMessage: action.payload.message
      }
    }
    default: {
      return state
    }
  }
}
