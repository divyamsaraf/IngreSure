export type DietType = 
  | "Hindu Veg" 
  | "Hindu Non-Veg" 
  | "Jain" 
  | "Vegan" 
  | "Halal" 
  | "Kosher" 
  | "Vegetarian"
  | "None"
  | string;

export interface UserProfile {
  diet: DietType;
  dairy_allowed: boolean;
  meat_allowed: boolean;
  allergies: string[];
  is_onboarding_completed: boolean;
}

export const DEFAULT_PROFILE: UserProfile = {
  diet: "None",
  dairy_allowed: true,
  meat_allowed: true,
  allergies: [],
  is_onboarding_completed: false
};
