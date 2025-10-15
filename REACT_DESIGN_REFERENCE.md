# React Design Reference - pctsb.syntra

This document captures the design patterns, component structure, and styling approach from the React project at `C:\Users\Arslan\Documents\Projects\tms-app\pctsb.syntra` to guide Angular frontend development.

## Project Overview

**Framework:** Next.js 14+ with React (App Router)
**Styling:** Tailwind CSS with custom theme
**UI Library:** shadcn/ui components (Radix UI primitives)
**Icons:** Lucide React icons
**State Management:** React Context + Hooks

## Color Palette & Theme

Based on the React project:

```scss
// Primary Colors (from Tailwind classes)
$primary: #[extracted from theme] // Primary brand color
$primary-foreground: white

// Semantic Colors
$success: #22c55e (green-500)
$success-light: #dcfce7 (green-100)
$warning: #eab308 (yellow-500)
$warning-light: #fef3c7 (yellow-100)
$danger: #ef4444 (red-500)
$info: #3b82f6 (blue-500)
$info-light: #dbeafe (blue-100)

// Neutral Colors
$amber: #f59e0b (amber-500)
$amber-light: #fef3c7 (amber-100)
$indigo: #6366f1 (indigo-600)
$indigo-light: #e0e7ff (indigo-100)

// Background & Muted
$muted: #f3f4f6 (gray-100)
$muted-foreground: #6b7280 (gray-500)
$accent: Light gray hover effect
```

## Typography

```scss
// Font Families
$font-family-base: System fonts (likely Inter or similar)

// Font Sizes
$text-xs: 0.75rem (12px)
$text-sm: 0.875rem (14px)
$text-md: 1rem (16px)
$text-lg: 1.125rem (18px)
$text-xl: 1.25rem (20px)
$text-2xl: 1.5rem (24px)
$text-3xl: 1.875rem (30px)
$text-4xl: 2.25rem (36px)
$text-5xl: 3rem (48px)

// Font Weights
$font-medium: 500
$font-semibold: 600
$font-bold: 700
```

## Spacing System

Based on Tailwind spacing scale:

```scss
$spacing-1: 0.25rem (4px)
$spacing-2: 0.5rem (8px)
$spacing-3: 0.75rem (12px)
$spacing-4: 1rem (16px)
$spacing-6: 1.5rem (24px)
$spacing-8: 2rem (32px)
$spacing-10: 2.5rem (40px)
$spacing-12: 3rem (48px)
```

## Component Patterns

### 1. Dashboard/Home Page

**File:** `pctsb.syntra/src/components/HomePage.tsx`

**Layout Structure:**
```
Hero Section (text-center, py-8 md:py-12)
├── Large Title (text-4xl md:text-5xl font-bold)
├── Tagline (text-lg md:text-xl text-muted-foreground)

Quick Actions Card (transparent, no shadow, no border)
├── Button Grid (flex-wrap, justify-center, gap-3 md:gap-4)
    ├── Create New TSR
    ├── Submit New Claim
    ├── Book Accommodation
    ├── Process Visa
    └── New Transport Request

Summary Cards Grid (grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6)
├── My Pending TSRs (yellow theme)
├── Visa Application Updates (blue theme)
├── My Draft Claims (amber theme)
├── Book Accommodation (indigo theme)
└── Book Transport (green theme)

Recent Activity Card (shadow-lg)
├── Header with Search & Refresh
└── Activity Items List
    └── Card per activity item (hover effect)
```

**Key Design Elements:**
- **Hero**: Centered text, large heading with colored brand name "SynTra"
- **Quick Actions**: Large buttons (w-48, size="lg") with icons and text
- **Summary Cards**: Icon in colored circle (top-right), large number (3xl font-bold), small description
- **Recent Activity**: Search bar + Refresh button, cards with icon circles, status badges

### 2. Summary Card Component

**File:** `pctsb.syntra/src/components/dashboard/SummaryCard.tsx`

**Structure:**
```typescript
Card (shadow-lg, hover effect)
├── CardHeader (flex-row, items-center, justify-between)
│   ├── CardTitle (text-base font-medium)
│   └── Icon in colored circle (p-2 rounded-md)
└── CardContent
    ├── Value (text-3xl font-bold text-primary)
    └── Description (text-xs text-muted-foreground)
```

**Props Pattern:**
- title: string
- value: string | number
- description?: string
- icon?: LucideIcon
- iconBgColor?: string (e.g., "bg-green-100 dark:bg-green-800/30")
- iconColor?: string (e.g., "text-green-600 dark:text-green-400")

**Design Specifications:**
- Card: `shadow-lg`, hover transitions
- Icon container: `p-2 rounded-md` with background color
- Icon: `h-5 w-5` with foreground color
- Value: `text-3xl font-bold text-primary`
- Description: `text-xs text-muted-foreground pt-1`

### 3. Activity Item Card

**Pattern:**
```typescript
Card (hover:bg-accent)
└── CardContent (p-4, flex items-center justify-between)
    ├── Icon Circle (p-3 rounded-full, conditional colors)
    ├── Content
    │   ├── Title (text-md font-semibold)
    │   └── Metadata (text-xs text-muted-foreground)
    └── Actions
        ├── Status Badge
        └── View Details Link
```

**Status-based Colors:**
- Approved: `bg-green-100 dark:bg-green-800/30`, icon: `text-green-600 dark:text-green-400`
- Default: `bg-muted/50`, icon: `text-primary`

### 4. Button Patterns

**Primary Button:**
```typescript
<Button size="lg" variant="default" className="w-48">
  <Icon className="mr-2 h-5 w-5" />
  Button Text
</Button>
```

**Variants:**
- `default`: Primary colored background
- `outline`: Border only
- `ghost`: Transparent, hover effect

**Sizes:**
- `sm`: Small (h-9, text-sm)
- `default`: Regular (h-10)
- `lg`: Large (h-11, text-base)

### 5. Card Component

**Base Pattern:**
```typescript
<Card className="shadow-lg">
  <CardHeader>
    <CardTitle className="text-2xl font-semibold">Title</CardTitle>
    <CardDescription className="mt-1">Description</CardDescription>
  </CardHeader>
  <CardContent className="pt-2">
    {/* Content */}
  </CardContent>
</Card>
```

**Variants:**
- Default: White background, subtle border, shadow
- Transparent: `bg-transparent shadow-none border-none`
- Hover: `hover:bg-accent hover:text-accent-foreground`

### 6. Input & Search Patterns

**Search Input:**
```typescript
<div className="relative w-full md:w-auto md:min-w-[300px]">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
  <Input
    type="search"
    placeholder="Search..."
    className="pl-10 pr-4 py-2 h-10 text-sm rounded-lg shadow-sm"
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
  />
</div>
```

## Icon Usage

**Icon Library:** Lucide React

**Common Icons:**
- `FileText`: Documents, general items
- `ClipboardList`: TSR/TRF requests
- `ReceiptText`: Claims, receipts
- `StickyNote`: Visa applications
- `Plane`: Flight bookings
- `BedDouble`: Accommodation
- `CarFront`: Transport
- `PlusCircle`: Create/Add actions
- `Search`: Search functionality
- `RefreshCw`: Refresh actions
- `Loader2`: Loading states (with animate-spin)

**Icon Sizing:**
- Small: `h-4 w-4`
- Medium: `h-5 w-5`
- Large: `h-6 w-6`
- Extra Large: `h-8 w-8`, `h-12 w-12`

**Icon in Buttons:** `mr-2` for left spacing

## Layout Structure

**Main Layout Pattern:**
```
<div className="space-y-8">
  {/* Section 1 */}
  {/* Section 2 */}
  {/* Section 3 */}
</div>
```

**Grid Patterns:**
- Cards: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6`
- Responsive: Mobile-first with `sm:`, `md:`, `lg:` breakpoints

**Flexbox Patterns:**
- Centered: `flex justify-center items-center`
- Space between: `flex items-center justify-between`
- With gap: `flex gap-4`
- Wrap: `flex flex-wrap`

## Responsive Design

**Breakpoints:**
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

**Common Responsive Patterns:**
- Text: `text-4xl md:text-5xl`
- Padding: `py-8 md:py-12`
- Grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-5`
- Width: `w-full md:w-auto md:min-w-[300px]`
- Flex direction: `flex-col md:flex-row`

## Loading States

```typescript
{isLoading ? (
  <div className="py-10 flex justify-center items-center">
    <Loader2 className="h-8 w-8 animate-spin text-primary" />
  </div>
) : (
  {/* Content */}
)}
```

## Empty States

```typescript
<div className="py-10 text-center">
  <div className="text-muted-foreground mb-4">
    <Icon className="h-12 w-12 mx-auto mb-4 opacity-50" />
    <p className="text-lg font-medium">No items found</p>
    <p className="text-sm">Descriptive message here.</p>
  </div>
</div>
```

## Error States

```typescript
{error ? (
  <div className="py-10 text-center text-red-500">
    {error}
  </div>
) : null}
```

## Dark Mode Support

All components support dark mode with Tailwind's `dark:` prefix:

```scss
// Example patterns
.card {
  bg-white dark:bg-gray-900
}
.text {
  text-gray-800 dark:text-white
}
.muted {
  text-gray-500 dark:text-gray-400
}
.icon-bg {
  bg-green-100 dark:bg-green-800/30
}
.icon {
  text-green-600 dark:text-green-400
}
```

## Animation & Transitions

**Hover Effects:**
```scss
hover:bg-accent hover:text-accent-foreground
transition-shadow duration-300
```

**Spin Animation:**
```scss
animate-spin // For loading spinners
```

**Transform:**
```scss
-translate-y-1/2 // For centering icons
```

## Angular Migration Mapping

| React Component | Angular Equivalent | Notes |
|----------------|-------------------|-------|
| `HomePage.tsx` | `dashboard.component.ts` | May need to be created |
| `SummaryCard.tsx` | Reusable card component | Create if missing |
| `Card`, `Button`, `Input` | Angular Material or custom components | Match shadcn/ui styling |
| Tailwind classes | SCSS with utility classes | Create utility classes or use Angular CDK |
| `useState`, `useEffect` | Component properties, lifecycle hooks | Standard Angular patterns |
| `fetch` API calls | HttpClient service | Use existing services |

## Module Structure Reference

**React Project Structure:**
```
src/
├── app/ (Next.js App Router)
│   ├── accommodation/
│   ├── admin/
│   ├── claims/
│   ├── notifications/
│   ├── reports/
│   ├── transport/
│   ├── trf/
│   └── visa/
├── components/
│   ├── accommodation/
│   ├── admin/
│   ├── claims/
│   ├── dashboard/
│   ├── notifications/
│   ├── transport/
│   ├── trf/
│   ├── visa/
│   └── ui/ (shadcn/ui components)
└── lib/ (utilities)
```

**Angular Equivalent:**
```
frontend/src/app/
├── features/
│   ├── dashboard/ (TO BE CREATED/REVISED)
│   ├── admin/
│   ├── expense-claims/
│   ├── requests/
│   │   ├── accommodation/
│   │   ├── travel/
│   │   └── visa/
│   └── trf-management/
├── shared/
│   └── components/
└── core/
    └── services/
```

## Next Steps for Angular Development

1. **Review existing Angular components** - Check what already exists
2. **Create/enhance Dashboard component** - Match HomePage.tsx layout and functionality
3. **Create reusable UI components** - Match shadcn/ui card, button, input styles
4. **Apply consistent styling** - Match Tailwind color palette and spacing
5. **Integrate with backend APIs** - Use existing services (insights.service.ts)
6. **Test responsive behavior** - Match mobile/tablet/desktop breakpoints
7. **Add dark mode support** - If needed based on project requirements

---

**Reference Files:**
- Main Dashboard: `pctsb.syntra/src/components/HomePage.tsx`
- Summary Card: `pctsb.syntra/src/components/dashboard/SummaryCard.tsx`
- Layout: `pctsb.syntra/src/app/layout.tsx`
- Global Styles: `pctsb.syntra/src/app/globals.css`
- Tailwind Config: `pctsb.syntra/tailwind.config.ts`
